package com.qoobot.qoocommunity.event.dto.request;

import lombok.Data;

@Data
public class RegistrationRequest {

    private String name;
    private String company;
    private String title;
    private String email;
}
