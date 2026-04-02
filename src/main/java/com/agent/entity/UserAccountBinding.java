package com.agent.entity;

import java.time.LocalDateTime;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.Data;

@Data
@TableName("user_account_binding")
public class UserAccountBinding {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long agentUserId;
    private Long hmdpUserId;
    private Long skyTakeOutUserId;
    private String hmdpToken;
    private String skyTakeOutToken;
    private Integer bindStatus;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
