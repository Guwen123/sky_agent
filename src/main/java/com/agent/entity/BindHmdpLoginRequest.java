package com.agent.entity;

import lombok.Data;

@Data
public class BindHmdpLoginRequest {
    private String phone;
    private String code;
    private String password;
}

