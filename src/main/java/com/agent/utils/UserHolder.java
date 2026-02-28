package com.agent.utils;

import com.agent.entity.User;

public class UserHolder {
    
    // 使用ThreadLocal保存当前登录用户信息
    private static final ThreadLocal<User> userHolder = new ThreadLocal<>();
    
    // 保存用户信息到当前线程
    public static void setUser(User user) {
        userHolder.set(user);
    }
    
    // 从当前线程获取用户信息
    public static User getUser() {
        return userHolder.get();
    }
    
    // 获取当前登录用户ID
    public static Long getUserId() {
        User user = userHolder.get();
        return user != null ? user.getId() : null;
    }
    
    // 获取当前登录用户名
    public static String getUsername() {
        User user = userHolder.get();
        return user != null ? user.getUsername() : null;
    }
    
    // 清除当前线程的用户信息（防止内存泄漏）
    public static void removeUser() {
        userHolder.remove();
    }
}