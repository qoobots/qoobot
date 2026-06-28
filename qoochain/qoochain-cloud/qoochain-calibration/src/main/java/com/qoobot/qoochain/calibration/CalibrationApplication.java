package com.qoobot.qoochain.calibration;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = {"com.qoobot.qoochain.calibration", "com.qoobot.qoochain.common"})
public class CalibrationApplication {
    public static void main(String[] args) {
        SpringApplication.run(CalibrationApplication.class, args);
    }
}
