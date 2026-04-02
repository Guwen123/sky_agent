<template>
  <div class="login-page">
    <div class="login-backdrop" aria-hidden="true"></div>
    <div class="login-veil"></div>

    <div class="login-card glass-panel">
      <div class="brand">
        <h1>智能生活助手</h1>
        <p>登录后开启你的生活服务助手。</p>
      </div>

      <form class="form" @submit.prevent="handleSubmit">
        <label>
          用户名
          <input v-model.trim="form.username" type="text" placeholder="请输入用户名" required />
        </label>

        <label>
          密码
          <input v-model="form.password" type="password" placeholder="请输入密码" required />
        </label>

        <label>
          验证码
          <div class="captcha-row">
            <input v-model.trim="form.captcha" type="text" placeholder="请输入验证码" required />
            <button class="secondary" type="button" :disabled="currentCaptchaState.isSending" @click="sendCaptcha">
              {{ currentCaptchaState.isSending ? `${currentCaptchaState.countdown}s` : '获取验证码' }}
            </button>
          </div>
        </label>

        <button class="primary" :disabled="loading" type="submit">
          {{ loading ? '提交中...' : (isLogin ? '登录' : '注册') }}
        </button>
      </form>

      <div class="switch-line">
        <span>{{ isLogin ? '没有账号？' : '已有账号？' }}</span>
        <button type="button" @click="isLogin = !isLogin">{{ isLogin ? '去注册' : '去登录' }}</button>
      </div>

      <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

const API_BASE = ''

function createCaptchaState() {
  return {
    isSending: false,
    countdown: 60,
    timer: null,
  }
}

export default {
  name: 'LoginPage',
  data() {
    return {
      isLogin: true,
      loading: false,
      errorMsg: '',
      form: {
        username: '',
        password: '',
        captcha: ''
      },
      captchaState: {
        login: createCaptchaState(),
        register: createCaptchaState(),
      },
    }
  },
  computed: {
    sceneKey() {
      return this.isLogin ? 'login' : 'register'
    },
    currentCaptchaState() {
      return this.captchaState[this.sceneKey]
    }
  },
  beforeUnmount() {
    Object.values(this.captchaState).forEach((item) => {
      if (item.timer) clearInterval(item.timer)
    })
  },
  methods: {
    async sendCaptcha() {
      this.errorMsg = ''
      if (!this.form.username) {
        this.errorMsg = '请先输入用户名。'
        return
      }
      const state = this.currentCaptchaState
      try {
        state.isSending = true
        const scenePath = this.isLogin ? '/api/captcha/login' : '/api/captcha/register'
        const requestUrl = `${API_BASE}${scenePath}`
        const { data } = await axios.get(requestUrl, {
          timeout: 10000,
          params: { username: this.form.username }
        })
        if (data.code !== 200) {
          this.errorMsg = data.message || '验证码发送失败'
          state.isSending = false
          return
        }
        this.startCountdown(state)
      } catch (error) {
        this.errorMsg = error?.response?.data?.message || error.message || '验证码发送失败'
        state.isSending = false
      }
    },
    startCountdown(state) {
      if (state.timer) clearInterval(state.timer)
      state.countdown = 60
      state.timer = setInterval(() => {
        state.countdown -= 1
        if (state.countdown <= 0) {
          clearInterval(state.timer)
          state.timer = null
          state.isSending = false
        }
      }, 1000)
    },
    async handleSubmit() {
      this.errorMsg = ''
      this.loading = true
      try {
        const endpoint = this.isLogin ? '/api/login' : '/api/register'
        const { data } = await axios.post(`${API_BASE}${endpoint}`, this.form)
        if (data.code !== 200) {
          this.errorMsg = data.message || '操作失败'
          return
        }
        if (this.isLogin && data.data) {
          localStorage.setItem('token', data.data)
          this.$router.push('/agent')
        } else {
          this.isLogin = true
          this.errorMsg = '注册成功，请登录。'
        }
      } catch (error) {
        this.errorMsg = error?.response?.data?.message || error.message || '请求失败'
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  overflow: hidden;
}

.login-backdrop,
.login-veil {
  position: absolute;
  inset: 0;
}

.login-backdrop {
  background-image:
    linear-gradient(135deg, rgba(18, 33, 26, 0.16), rgba(247, 224, 136, 0.16)),
    var(--scene-backdrop);
  background-size: cover;
  background-position: center;
  transform: scale(1.02);
  filter: saturate(1.02) contrast(1.02);
  opacity: 1;
}

.login-veil {
  background:
    linear-gradient(180deg, rgba(14, 31, 28, 0.12), rgba(10, 20, 32, 0.34)),
    radial-gradient(circle at 25% 18%, rgba(255, 248, 196, 0.18), transparent 28%);
}

.glass-panel {
  position: relative;
  z-index: 1;
  background: linear-gradient(165deg, rgba(255, 255, 255, 0.23), rgba(255, 255, 255, 0.11));
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 20px 60px rgba(6, 12, 26, 0.35);
  backdrop-filter: blur(16px);
}

.login-card {
  width: min(94vw, 500px);
  border-radius: 24px;
  padding: 30px;
  color: #eef6ff;
}

.brand h1 {
  margin: 0;
  font-size: 34px;
  letter-spacing: 1px;
}

.brand p {
  margin: 8px 0 22px;
  font-size: 14px;
  color: rgba(238, 246, 255, 0.86);
}

.form {
  display: grid;
  gap: 14px;
}

label {
  display: grid;
  gap: 8px;
  font-size: 14px;
}

input {
  width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 13px;
  padding: 11px 12px;
  font-size: 14px;
  color: #fff;
  background: rgba(9, 21, 40, 0.45);
}

input::placeholder {
  color: rgba(255, 255, 255, 0.62);
}

.captcha-row {
  display: grid;
  grid-template-columns: 1fr 130px;
  gap: 10px;
}

button {
  border: none;
  border-radius: 13px;
  padding: 11px 12px;
  font-weight: 600;
  cursor: pointer;
}

button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.primary {
  color: #f7fcff;
  background: linear-gradient(120deg, #1677ff 0%, #14b8a6 100%);
  box-shadow: 0 14px 28px rgba(20, 92, 191, 0.34);
}

.secondary {
  color: #f8fbff;
  background: linear-gradient(120deg, rgba(18, 49, 84, 0.92), rgba(31, 84, 140, 0.88));
  box-shadow: 0 12px 24px rgba(8, 23, 42, 0.28);
}

.switch-line {
  margin-top: 14px;
  display: flex;
  justify-content: center;
  gap: 8px;
  font-size: 14px;
}

.switch-line button {
  padding: 0;
  border: none;
  color: #ffffff;
  font-weight: 700;
  text-decoration: underline;
  text-underline-offset: 3px;
  background: transparent;
}

.error-msg {
  margin-top: 10px;
  font-size: 13px;
  color: #ffd3d3;
}

@media (max-width: 640px) {
  .captcha-row {
    grid-template-columns: 1fr;
  }
}
</style>
