#include "nrf_gpio.h"
#include "nrf_delay.h"
#include "nrf_drv_saadc.h"
#include "SEGGER_RTT.h"

#define PIN_SENSOR   3   // AIN1 = P0.03
#define PIN_CHARGE   4

static nrf_saadc_value_t adc_buf[1];
static volatile int16_t adc_result = 0;

void saadc_callback(nrf_drv_saadc_evt_t const * p_event)
{
    if (p_event->type == NRF_DRV_SAADC_EVT_DONE)
    {
        adc_result = p_event->data.done.p_buffer[0];
        nrf_drv_saadc_buffer_convert(adc_buf, 1);
    }
}

void saadc_init(void)
{
    nrf_drv_saadc_config_t config = NRF_DRV_SAADC_DEFAULT_CONFIG;
    nrf_drv_saadc_init(&config, saadc_callback);

    nrf_saadc_channel_config_t channel =
        NRF_DRV_SAADC_DEFAULT_CHANNEL_CONFIG_SE(NRF_SAADC_INPUT_AIN1);

    nrf_drv_saadc_channel_init(0, &channel);
    nrf_drv_saadc_buffer_convert(adc_buf, 1);
}

static inline int read_adc(void)
{
    nrf_drv_saadc_sample();
    nrf_delay_us(5);
    return adc_result;
}

void measure_capacitance(void)
{
    float capacitance_pf;
    int adc;

    // 1) SENSOR pin high-impedance
    nrf_gpio_cfg_input(PIN_SENSOR, NRF_GPIO_PIN_NOPULL);

    // 2) CHARGE pin high
    nrf_gpio_cfg_output(PIN_CHARGE);
    nrf_gpio_pin_set(PIN_CHARGE);

    // let the node charge
    nrf_delay_us(10);

    // 3) Read ADC
    adc = read_adc();

    // 4) Discharge
    nrf_gpio_pin_clear(PIN_CHARGE);
   // nrf_delay_us(10);

    // 5) Force SENSOR pin low (hard discharge)
    nrf_gpio_cfg_output(PIN_SENSOR);
    nrf_gpio_pin_clear(PIN_SENSOR);
    //nrf_delay_us(10);

    // 6) Compute capacitance using your formula
    if (adc < 1023)
        capacitance_pf = (adc * 400.0f) / (1023.0f - adc);
    else
        capacitance_pf = 0;

    // 7) Print result (RTT)
    //SEGGER_RTT_printf(0, "%d,%d\n", adc, (int)capacitance_pf);
// NEW — force output to channel 0 with no prefix:
//SEGGER_RTT_WriteString(0, "");
/*
char buf[32];
snprintf(buf, sizeof(buf), "%d,%d\n", adc, (int)capacitance_pf);
SEGGER_RTT_WriteString(0, buf);
*/
char buf[32];
snprintf(buf, sizeof(buf),"%d\n", (int)capacitance_pf);
SEGGER_RTT_WriteString(0, buf);

}

int main(void)
{
    SEGGER_RTT_Init();
    //SEGGER_RTT_WriteString(0, "Capacitive Sensor Test\n");

    saadc_init();

    while (1)
    {
        measure_capacitance();
        nrf_delay_ms(50);
    }
}
