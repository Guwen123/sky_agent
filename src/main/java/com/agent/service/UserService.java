package com.agent.service;

import com.agent.entity.Result;
import com.agent.entity.BindHmdpLoginRequest;
import com.agent.entity.BindSkyTakeOutLoginRequest;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

public interface UserService {
    public Result detail();

    public Result logout();
    
    public Result talk(String question);

    public StreamingResponseBody streamTalk(String question);

    public Result sendHmdpCode(String phone);

    public Result bindHmdp(BindHmdpLoginRequest request);

    public Result bindSkyTakeOut(BindSkyTakeOutLoginRequest request);

    public Result getExternalBinding();
}
