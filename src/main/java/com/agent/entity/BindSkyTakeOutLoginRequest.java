package com.agent.entity;

import java.io.Serializable;

import lombok.Data;

@Data
public class BindSkyTakeOutLoginRequest implements Serializable {
    private String code;
}

