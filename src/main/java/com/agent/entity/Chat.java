package com.agent.entity;

import lombok.Builder;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;

@Data
@Slf4j
@Builder
public class Chat {
    private String question;
    private String user_id;
}
