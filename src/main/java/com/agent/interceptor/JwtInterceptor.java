package com.agent.interceptor;

import com.agent.entity.Result;
import com.agent.entity.User;
import com.agent.mapper.UserMapper;
import com.agent.utils.JwtUtil;
import com.agent.utils.UserHolder;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.jsonwebtoken.Claims;
import org.springframework.web.servlet.HandlerInterceptor;
import org.springframework.web.servlet.ModelAndView;

import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.PrintWriter;

public class JwtInterceptor implements HandlerInterceptor {

    @Resource
    private UserMapper userMapper;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler)
            throws Exception {
        // 允许登录和验证码接口
        String path = request.getRequestURI();
        if (path.contains("/api/login") || path.contains("/api/captcha")) {
            return true;
        }

        // 获取Authorization头
        String token = request.getHeader("Authorization");
        if (token == null || token.isEmpty()) {
            // 没有token，返回401
            response.setContentType("application/json;charset=utf-8");
            PrintWriter writer = response.getWriter();
            writer.write(new ObjectMapper().writeValueAsString(Result.error(401, "未授权，请先登录")));
            writer.flush();
            writer.close();
            return false;
        }

        try {
            // 验证token并解析
            Claims claims = JwtUtil.parseToken(token);
            String username = claims.getSubject();

            // 从数据库查询用户信息
            QueryWrapper<User> queryWrapper = new QueryWrapper<>();
            queryWrapper.eq("username", username);
            User user = userMapper.selectOne(queryWrapper);

            // 将用户信息保存到ThreadLocal
            UserHolder.setUser(user);

            return true;
        } catch (Exception e) {
            // token无效，返回401
            response.setContentType("application/json;charset=utf-8");
            PrintWriter writer = response.getWriter();
            writer.write(new ObjectMapper().writeValueAsString(Result.error(401, "token无效或已过期")));
            writer.flush();
            writer.close();
            return false;
        }
    }

    @Override
    public void postHandle(HttpServletRequest request, HttpServletResponse response, Object handler,
            ModelAndView modelAndView) throws Exception {
        // 空实现
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex)
            throws Exception {
        // 请求完成后清除ThreadLocal中的用户信息，防止内存泄漏
        UserHolder.removeUser();
    }
}