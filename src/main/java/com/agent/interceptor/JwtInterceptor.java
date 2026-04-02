package com.agent.interceptor;

import com.agent.entity.Result;
import com.agent.entity.User;
import com.agent.mapper.UserMapper;
import com.agent.utils.JwtUtil;
import com.agent.utils.UserHolder;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.jsonwebtoken.Claims;

import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;
import org.springframework.web.servlet.ModelAndView;

import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.PrintWriter;

public class JwtInterceptor implements HandlerInterceptor {
    private final UserMapper userMapper;

    public JwtInterceptor(UserMapper userMapper) {
        this.userMapper = userMapper;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler)
            throws Exception {
        System.out.println("开始拦截");

        String token = request.getHeader("Authorization");
        System.out.println(token);
        if (token == null || token.isEmpty()) {
            response.setContentType("application/json;charset=utf-8");
            PrintWriter writer = response.getWriter();
            writer.write(new ObjectMapper().writeValueAsString(Result.error(401, "未授权，请先登录")));
            writer.flush();
            writer.close();
            return false;
        }

        try {
            System.out.println("开始验证token");
            if (token.startsWith("Bearer ")) {
                token = token.substring(7);
            }

            Claims claims = JwtUtil.parseToken(token);
            String username = claims.getSubject();

            QueryWrapper<User> queryWrapper = new QueryWrapper<>();
            queryWrapper.eq("username", username);
            User user = userMapper.selectOne(queryWrapper);
            if (user == null) {
                throw new RuntimeException("token对应用户不存在");
            }

            UserHolder.setUser(user);
            return true;
        } catch (Exception e) {
            System.out.println("token无效或已过期: " + e.getMessage());
            response.setContentType("application/json;charset=utf-8");
            PrintWriter writer = response.getWriter();
            writer.write(new ObjectMapper().writeValueAsString(Result.error(401, "token无效或已过期")));
            writer.flush();
            writer.close();
            return false;
        }
    }
}
