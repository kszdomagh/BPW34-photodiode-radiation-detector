#include <stdio.h>
#include <stdlib.h>
#include "pico/stdlib.h"
#include "hardware/gpio.h"
#include "hardware/adc.h"
#include "pico/cyw43_arch.h"


#define N_SAMPLES 50000 // with 500ksps it takes 0.1s to capture
#define DEFAULT_THRESHOLD 1000
#define LED_PIN 25


uint16_t sample_buf[N_SAMPLES];
uint16_t threshold = DEFAULT_THRESHOLD;
uint8_t peak_capture_mode = 0;
uint8_t capture_all_mode = 0;
uint8_t samples_over_threshold = 0;

void printhelp(void)
{
    puts("===================================================================");
    puts("         commands          ");
    puts("===================================================================");
    puts("tX, ...\t: set threshold ");
    puts("s\t: capture one buffer and print stats");
    puts("a\t: capture all mode: sample 50k samples and print all values");
    puts("p\t: peak capture mode: sample 50k samples");
    puts("h\t: print help");
    puts("i\t: print info");
}

void printinfo(void)
{
    puts("===================================================================");
    puts("        information        ");
    puts("===================================================================");
    puts("RP2350 ADC and console control to be used with custom designed AFE");
    printhelp();
    puts("===================================================================");
    puts("        SKNF BOZON         ");
    puts("===================================================================");


}

void __not_in_flash_func(adc_capture)(uint16_t *buf, size_t count)
{
    adc_fifo_setup(true, false, 0, false, false);
    adc_run(true);
    for (size_t i = 0; i < count; i = i + 1)
        buf[i] = adc_fifo_get_blocking();
    adc_run(false);
    adc_fifo_drain();
}


void peak_capture_mode_func(void)
{
    int c = getchar_timeout_us(0);

    if (c != PICO_ERROR_TIMEOUT)
    {
        printf("%c", (char)c);
        if ((char)c == 'p')
        {
            peak_capture_mode = 0;
            printf("\npeak capture mode: OFF\n");
        }
     }

    adc_capture(sample_buf, N_SAMPLES);
    samples_over_threshold = 0;
    for (int i = 1; i < N_SAMPLES - 1; i++) 
    {
        // TODO: find the best way to capture peaks and preserve instanenious noise value before peak 
        // maybe calculate the mean avg of the laxt X samples before peak and treat this val as some dc offset
        if ((sample_buf[i-1] > threshold) && (sample_buf[i] > threshold) && (sample_buf[i+1] > threshold)) {
            if (sample_buf[i] >= sample_buf[i-1] && sample_buf[i] >= sample_buf[i+1]) {
                printf("p: %u\n", sample_buf[i]);
                samples_over_threshold++;
            }
        }
    }
    if(samples_over_threshold > 0)
    {
        printf("counts: %u\n", samples_over_threshold);
    }
}


void capture_all_mode_func(void)
{
    int c = getchar_timeout_us(0);

    if (c != PICO_ERROR_TIMEOUT)
    {
        printf("%c", (char)c);
        if ((char)c == 'a')
        {
            peak_capture_mode = 0;
            printf("\ncapture all mode: OFF\n");
        }
     }
    adc_capture(sample_buf, N_SAMPLES);
    for (int i = 1; i < N_SAMPLES - 1; i++) 
    {
        printf("p: %u\n", sample_buf[i]);
    }
}

int main(void)
{
    stdio_init_all();
    adc_init();
    cyw43_arch_init();
    adc_set_temp_sensor_enabled(false); // mayb lower noise
    
    gpio_set_dir_all_bits(0);

    for (int i = 2; i < 30; ++i)
    {
        gpio_set_function(i, GPIO_FUNC_SIO);
        if (i >= 26) {
            gpio_disable_pulls(i);
            gpio_set_input_enabled(i, false);
        }
    }

    gpio_set_dir(LED_PIN, GPIO_OUT);

    /*
    printf("\n===========================\n");
    printf("RP2350 ADC and Console control\n");
    printf("===========================\n");
    printhelp();
    */

    while (1)
    {
    
        if(peak_capture_mode == 1)
        {
            peak_capture_mode_func();
            continue;
        } else if(capture_all_mode == 1)
        {
            capture_all_mode_func();
            continue;
        }
        
        char c = getchar();
        printf("%c\n", c); //  printing command

        switch (c) {
            
            /*  set threshold to a set value (eg. th967)  */
            case 't':{
                char buf[8];
                int idx = 0;
                
                while (idx < (int)(sizeof(buf) - 1))
                {
                    c = getchar();
                    printf("%c", c);
                    if (c == '\r' || c == '\n') break;
                    if (c >= '0' && c <= '9') {
                        buf[idx++] = c;
                    } else {
                        puts("\ninvalid character\n");
                        printhelp();
                        goto done;
                    }
                }

                buf[idx] = '\0';
                int val = atoi(buf);

                if (val < 0 || val > 4095) {
                    puts("\nout of range (0–4095)\n");
                    printhelp();
                } else {
                    threshold = (uint16_t)val;
                    printf("\nthreshold set to %d\n", threshold);
                }
                done:
                break;
            }

            /*  sample one buffer and print stats for detetmining baseline/noise   */
            case 's':{
                puts("starting capture");
                adc_capture(sample_buf, N_SAMPLES);
                puts("done");
                
                uint16_t min_val = sample_buf[0];
                uint16_t max_val = sample_buf[0];
                uint32_t sum = 0;
                
                for (int i = 0; i < N_SAMPLES; i++)
                {
                    //printf("%d\n", sample_buf[i]);    // do not print values
                    if (sample_buf[i] < min_val) min_val = sample_buf[i];
                    if (sample_buf[i] > max_val) max_val = sample_buf[i];
                    sum += sample_buf[i];
                }
                printf("min: %d\n", min_val);
                printf("max: %d\n", max_val);
                printf("abs: %d\n", max_val - min_val);
                printf("avg: %d\n", sum / N_SAMPLES);
                break;
            }

            /*  peak capture mode   */
            case 'p': {
                capture_all_mode = 0;
                peak_capture_mode = !peak_capture_mode;
                if(peak_capture_mode){
                    puts("peak capture mode: ON");
                    printf("threshold %d\n", threshold);
                } else {
                    puts("peak capture mode: OFF");
                }
                break;
            }
            
            /*  send all samples mode   */
            case 'a': {
                peak_capture_mode = 0;
                capture_all_mode = !capture_all_mode;
                if(capture_all_mode){
                    puts("capture all mode: ON");
                    printf("threshold %d\n", threshold);
                } else {
                    puts("capture all mode: OFF");
                }
                break;
            }

            /*  helpguide   */
            case 'h':
                printhelp();
                break;

            case 'i':
                printinfo();
                break;
            
            default:
                break;
        }
    }
}