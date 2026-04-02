package com.agent.controller;

import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestMapping;

import javax.annotation.Resource;
import java.nio.charset.StandardCharsets;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import com.agent.entity.Result;
import com.agent.entity.BindHmdpLoginRequest;
import com.agent.entity.BindSkyTakeOutLoginRequest;
import com.agent.service.UserService;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestBody;

@RestController
@RequestMapping("/user")
public class UserController {
    @Resource
    private UserService userService;

    @PostMapping("/detail")
    public Result detail() {
        return userService.detail();
    }

    @GetMapping("/logout")
    public Result logout() {
        return userService.logout();
    }

    @GetMapping("/talk")
    public Result talk(@RequestParam String question) {
        return userService.talk(question);
    }

    @GetMapping(value = "/talk/stream", produces = MediaType.TEXT_PLAIN_VALUE)
    public ResponseEntity<StreamingResponseBody> talkStream(@RequestParam String question) {
        return ResponseEntity.ok()
                .contentType(new MediaType("text", "plain", StandardCharsets.UTF_8))
                .body(userService.streamTalk(question));
    }

    @PostMapping("/bind/hmdp/code")
    public Result sendHmdpCode(@RequestParam String phone) {
        return userService.sendHmdpCode(phone);
    }

    @PostMapping("/bind/hmdp/login")
    public Result bindHmdp(@RequestBody BindHmdpLoginRequest request) {
        return userService.bindHmdp(request);
    }

    @PostMapping("/bind/sky-take-out/login")
    public Result bindSkyTakeOut(@RequestBody BindSkyTakeOutLoginRequest request) {
        return userService.bindSkyTakeOut(request);
    }

    @GetMapping("/bind/external")
    public Result getExternalBinding() {
        return userService.getExternalBinding();
    }

}
