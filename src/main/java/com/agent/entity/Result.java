package com.agent.entity;

import lombok.Data;

@Data
public class Result {
    private int code;
    private String message;
    private Object data;

    private Result(int code, String message, Object data) {
        this.code = code;
        this.message = message;
        this.data = data;
    }

    // 成功响应
    public static Result ok() {
        return new Result(200, "操作成功", null);
    }

    public static Result ok(Object data) {
        return new Result(200, "操作成功", data);
    }

    public static Result ok(String message, Object data) {
        return new Result(200, message, data);
    }

    // 失败响应
    public static Result error(int code, String message) {
        return new Result(code, message, null);
    }

    public static Result error(String message) {
        return new Result(500, message, null);
    }

    // 自定义响应
    public static Result of(int code, String message, Object data) {
        return new Result(code, message, data);
    }
}