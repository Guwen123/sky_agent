<template>
  <div class="agent-page">
    <div class="scene-image"></div>
    <div class="scene-veil"></div>

    <header class="topbar chrome-panel">
      <div class="brand">
        <div class="brand-mark">
          <span></span>
        </div>
        <div class="brand-copy">
          <h1>Nova Agent</h1>
          <div class="brand-meta">
            <span class="profile-chip">{{ profile.username || 'Guest' }}</span>
            <span class="status-chip">ONLINE</span>
          </div>
        </div>
      </div>

      <div class="top-actions">
        <button class="ghost-btn" @click="settingsOpen = true">设置</button>
        <button class="danger-btn" @click="logout">退出</button>
      </div>
    </header>

    <main class="console chrome-panel">
      <div class="chat-body" ref="chatWindow">
        <div
          v-for="msg in messages"
          :id="`msg-${msg.id}`"
          :key="msg.id"
          :class="['msg', msg.role, { streaming: msg.id === streamingMessageId }]"
        >
          <div v-if="msg.role !== 'system'" class="avatar">
            {{ avatarLabel(msg.role) }}
          </div>
          <div class="bubble">
            {{ msg.content }}
            <div v-if="msg.orderConfirmation" class="order-confirm-card">
              <div class="order-confirm-line">
                <span>店铺</span>
                <strong>{{ msg.orderConfirmation.shopName || '-' }}</strong>
              </div>
              <div class="order-confirm-line">
                <span>地址</span>
                <strong>{{ msg.orderConfirmation.address || '-' }}</strong>
              </div>
              <div class="order-confirm-line">
                <span>收货人</span>
                <strong>{{ formatContact(msg.orderConfirmation) }}</strong>
              </div>
              <div class="order-confirm-items">
                <span>菜品</span>
                <div
                  v-for="(item, index) in msg.orderConfirmation.items || []"
                  :key="`${msg.id}-item-${index}`"
                  class="order-confirm-item"
                >
                  {{ item.display_text || `${item.name} x${item.quantity || 1}` }}
                </div>
              </div>
              <div class="order-confirm-actions">
                <button
                  class="primary-btn"
                  :disabled="sending"
                  @click="sendOrderDecision(msg.orderConfirmation.confirmText || '确认下单')"
                >
                  确认下单
                </button>
                <button
                  class="ghost-btn"
                  :disabled="sending"
                  @click="sendOrderDecision(msg.orderConfirmation.cancelText || '取消下单')"
                >
                  取消下单
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="composer-shell">
        <transition name="quick-fade">
          <div v-if="quickActionsOpen" class="quick-actions-pop chrome-panel">
            <div class="quick-actions-head">
              <span>快捷功能</span>
              <small>点一下就会直接填入并发送</small>
            </div>
            <div class="quick-actions">
              <button
                v-for="item in quickActions"
                :key="item.label"
                type="button"
                class="quick-btn"
                :disabled="sending"
                @mousedown.prevent
                @click="ask(item.prompt)"
              >
                {{ item.label }}
              </button>
            </div>
          </div>
        </transition>

        <div class="composer">
          <input
            v-model="input"
            :disabled="sending"
            @focus="openQuickActions"
            @blur="scheduleQuickActionsClose"
            @keyup.enter="send"
            placeholder="直接说想找什么"
          />
          <button class="send-btn" :disabled="sending" @click="send">
            {{ sending ? '传输中' : '发送' }}
          </button>
        </div>
      </div>
    </main>

    <transition name="slide">
      <div v-if="settingsOpen" class="settings-mask" @click.self="settingsOpen = false">
        <div class="settings-panel chrome-panel">
          <div class="settings-head">
            <h2>设置</h2>
            <button class="ghost-btn" @click="settingsOpen = false">关闭</button>
          </div>

          <div class="settings-card">
            <div class="setting-line">
              <span>用户名</span>
              <strong>{{ profile.username || '-' }}</strong>
            </div>
            <div class="setting-line">
              <span>ID</span>
              <strong>{{ profile.id || '-' }}</strong>
            </div>
            <button class="refresh-btn" @click="loadBinding">刷新</button>
          </div>

          <div class="settings-card">
            <h4>hmdp</h4>
            <div v-if="binding.hmdp_user_id || binding.hmdp_token || binding.hmdp_bound" class="setting-line">
              <span>当前绑定</span>
              <strong>{{ bindingDisplay('hmdp') }}</strong>
            </div>
            <div v-if="isBound('hmdp') && !rebindState.hmdp" class="binding-actions">
              <button class="ghost-btn" @click="openRebind('hmdp')">重新绑定</button>
            </div>
            <template v-if="!isBound('hmdp') || rebindState.hmdp">
              <div class="row">
                <input v-model.trim="hmdp.phone" placeholder="手机号" />
                <button class="ghost-btn" @click="sendHmdpCode">验证码</button>
              </div>
              <div class="row">
                <input v-model.trim="hmdp.code" placeholder="验证码" />
                <input v-model="hmdp.password" type="password" placeholder="密码" />
              </div>
              <div class="binding-actions">
                <button class="primary-btn" @click="bindHmdp">绑定 hmdp</button>
                <button v-if="isBound('hmdp')" class="ghost-btn" @click="closeRebind('hmdp')">取消</button>
              </div>
            </template>
            <p v-else class="binding-tip">当前账号已绑定，验证码和密码输入框已隐藏。</p>
          </div>

          <div class="settings-card">
            <h4>sky_take_out</h4>
            <div v-if="binding.sky_take_out_user_id || binding.sky_take_out_token || binding.sky_take_out_bound" class="setting-line">
              <span>当前绑定</span>
              <strong>{{ bindingDisplay('sky') }}</strong>
            </div>
            <div v-if="isBound('sky') && !rebindState.sky" class="binding-actions">
              <button class="ghost-btn" @click="openRebind('sky')">重新绑定</button>
            </div>
            <template v-if="!isBound('sky') || rebindState.sky">
              <input v-model.trim="sky.code" placeholder="微信登录 code" />
              <div class="binding-actions">
                <button class="primary-btn" @click="bindSky">绑定 sky_take_out</button>
                <button v-if="isBound('sky')" class="ghost-btn" @click="closeRebind('sky')">取消</button>
              </div>
            </template>
            <p v-else class="binding-tip">当前账号已绑定，微信登录 code 输入框已隐藏。</p>
          </div>

          <div class="settings-card tokens">
            <div class="setting-line">
              <span>hmdp_user_id</span>
              <strong>{{ binding.hmdp_user_id ?? '-' }}</strong>
            </div>
            <div class="setting-line">
              <span>sky_user_id</span>
              <strong>{{ binding.sky_take_out_user_id ?? '-' }}</strong>
            </div>
            <div class="setting-line">
              <span>hmdp_token</span>
              <strong>{{ maskToken(binding.hmdp_token) }}</strong>
            </div>
            <div class="setting-line">
              <span>sky_token</span>
              <strong>{{ maskToken(binding.sky_take_out_token) }}</strong>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
import axios from 'axios'

const API = ''
const ORDER_CONFIRMATION_PREFIX = '__ORDER_CONFIRMATION__'

export default {
  name: 'AgentPage',
  data() {
    return {
      profile: {},
      binding: {},
      settingsOpen: false,
      hmdp: { phone: '', code: '', password: '' },
      sky: { code: '' },
      rebindState: { hmdp: false, sky: false },
      input: '',
      sending: false,
      messages: [],
      msgIdSeed: 1,
      streamingMessageId: null,
      quickActionsOpen: false,
      quickActionsCloseTimer: null,
      quickActions: [
        { label: '热门博客', prompt: '请帮我查看最热门的博客' },
        { label: '历史博客', prompt: '请帮我查看我的历史博客' },
        { label: '历史订单', prompt: '请帮我查看我的历史下单信息' },
        { label: '绑定信息', prompt: '请读取我绑定的token和用户名' },
      ],
    }
  },
  beforeUnmount() {
    if (this.quickActionsCloseTimer) clearTimeout(this.quickActionsCloseTimer)
  },
  async mounted() {
    if (!localStorage.getItem('token')) {
      this.$router.push('/login')
      return
    }
    await this.loadProfile()
    await this.loadBinding()
    this.loadHistory()
    if (!this.messages.length) {
      this.pushMsg('system', '想吃什么，直接说。')
    }
  },
  methods: {
    authHeader() {
      return { Authorization: localStorage.getItem('token') }
    },
    avatarLabel(role) {
      if (role === 'user') return 'YOU'
      if (role === 'agent') return 'AI'
      return 'SYS'
    },
    storageKey() {
      return `chat_history_${this.profile.id || 'guest'}`
    },
    saveHistory() {
      localStorage.setItem(this.storageKey(), JSON.stringify(this.messages))
    },
    loadHistory() {
      try {
        const raw = localStorage.getItem(this.storageKey())
        const arr = raw ? JSON.parse(raw) : []
        if (Array.isArray(arr)) {
          this.messages = arr.map(msg => this.decorateSpecialMessage(msg))
          this.msgIdSeed = (arr[arr.length - 1]?.id || 0) + 1
        }
      } catch {
        this.messages = []
      }
      this.scrollBottom()
    },
    pushMsg(role, content) {
      this.messages.push(this.decorateSpecialMessage({ id: this.msgIdSeed++, role, content }))
      this.saveHistory()
      this.scrollBottom()
    },
    decorateSpecialMessage(message) {
      if (!message || message.role !== 'agent') return message

      const rawContent = typeof message.rawContent === 'string' ? message.rawContent : message.content
      if (typeof rawContent !== 'string' || !rawContent.startsWith(ORDER_CONFIRMATION_PREFIX)) {
        return message
      }

      try {
        const payload = JSON.parse(rawContent.slice(ORDER_CONFIRMATION_PREFIX.length))
        return {
          ...message,
          rawContent,
          orderConfirmation: payload,
          content: payload.message || '请确认以下订单信息',
        }
      } catch {
        return message
      }
    },
    formatContact(orderConfirmation) {
      const consignee = orderConfirmation?.consignee || '-'
      const phone = orderConfirmation?.phone || ''
      return `${consignee}${phone ? ` ${phone}` : ''}`
    },
    async loadProfile() {
      const { data } = await axios.post(`${API}/user/detail`, {}, { headers: this.authHeader() })
      if (data.code === 200) this.profile = data.data || {}
    },
    async loadBinding() {
      try {
        const { data } = await axios.get(`${API}/user/bind/external`, { headers: this.authHeader() })
        if (data.code === 200) {
          this.binding = data.data || {}
          this.resetBoundInputs()
        }
      } catch {
        this.binding = {}
      }
    },
    isBound(service) {
      if (service === 'hmdp') {
        return !!(this.binding.hmdp_user_id || this.binding.hmdp_token || this.binding.hmdp_bound)
      }
      return !!(this.binding.sky_take_out_user_id || this.binding.sky_take_out_token || this.binding.sky_take_out_bound)
    },
    openRebind(service) {
      this.rebindState[service] = true
    },
    closeRebind(service) {
      this.rebindState[service] = false
      this.resetBoundInputs()
    },
    resetBoundInputs() {
      if (!this.rebindState.hmdp) {
        this.hmdp = { phone: '', code: '', password: '' }
      }
      if (!this.rebindState.sky) {
        this.sky = { code: '' }
      }
      if (this.isBound('hmdp')) {
        this.hmdp = this.rebindState.hmdp ? this.hmdp : { phone: '', code: '', password: '' }
      }
      if (this.isBound('sky')) {
        this.sky = this.rebindState.sky ? this.sky : { code: '' }
      }
    },
    async sendHmdpCode() {
      const { data } = await axios.post(
        `${API}/user/bind/hmdp/code`,
        null,
        { params: { phone: this.hmdp.phone }, headers: this.authHeader() },
      )
      this.pushMsg('system', data.message || '验证码已发送')
    },
    async bindHmdp() {
      const { data } = await axios.post(`${API}/user/bind/hmdp/login`, this.hmdp, { headers: this.authHeader() })
      this.pushMsg('system', data.message || 'hmdp 绑定完成')
      this.rebindState.hmdp = false
      await this.loadBinding()
    },
    async bindSky() {
      const { data } = await axios.post(`${API}/user/bind/sky-take-out/login`, this.sky, { headers: this.authHeader() })
      this.pushMsg('system', data.message || 'sky_take_out 绑定完成')
      this.rebindState.sky = false
      await this.loadBinding()
    },
    openQuickActions() {
      if (this.quickActionsCloseTimer) {
        clearTimeout(this.quickActionsCloseTimer)
        this.quickActionsCloseTimer = null
      }
      this.quickActionsOpen = true
    },
    scheduleQuickActionsClose() {
      if (this.quickActionsCloseTimer) clearTimeout(this.quickActionsCloseTimer)
      this.quickActionsCloseTimer = setTimeout(() => {
        this.quickActionsOpen = false
      }, 120)
    },
    ask(text) {
      if (this.sending) return
      this.quickActionsOpen = false
      this.input = text
      this.send()
    },
    sendOrderDecision(text) {
      if (this.sending) return
      this.input = text
      this.send()
    },
    async send() {
      const question = this.input.trim()
      if (!question || this.sending) return
      this.quickActionsOpen = false
      this.input = ''
      this.sending = true

      this.pushMsg('user', question)
      const ai = { id: this.msgIdSeed++, role: 'agent', content: '' }
      this.messages.push(ai)
      this.streamingMessageId = ai.id
      this.saveHistory()
      this.scrollBottom()

      try {
        const streamed = await this.tryStream(question, ai)
        if (!streamed) {
          const { data } = await axios.get(`${API}/user/talk`, {
            params: { question },
            headers: this.authHeader(),
          })
          ai.content = data?.data || data?.result || '无返回内容'
        }
      } catch (e) {
        ai.content = `请求失败: ${e.message || e}`
      } finally {
        Object.assign(ai, this.decorateSpecialMessage(ai))
        this.sending = false
        this.streamingMessageId = null
        this.saveHistory()
        this.scrollBottom()
      }
    },
    async tryStream(question, aiMsg) {
      try {
        const token = localStorage.getItem('token')
        const res = await fetch(`${API}/user/talk/stream?question=${encodeURIComponent(question)}`, {
          method: 'GET',
          headers: { Authorization: token },
        })
        if (!res.ok || !res.body) return false

        const reader = res.body.getReader()
        const decoder = new TextDecoder('utf-8')

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          if (value) {
            aiMsg.content += decoder.decode(value, { stream: true })
            this.saveHistory()
            this.scrollBottom()
          }
        }

        const tail = decoder.decode()
        if (tail) {
          aiMsg.content += tail
        }
        return aiMsg.content.length > 0
      } catch {
        return false
      }
    },
    maskToken(token) {
      if (!token) return '-'
      if (token.length <= 10) return token
      return `${token.slice(0, 6)}...${token.slice(-4)}`
    },
    bindingDisplay(service) {
      if (service === 'hmdp') {
        return this.binding.hmdp_display_name
          || this.binding.hmdp_username
          || this.binding.hmdp_phone
          || ((this.binding.hmdp_user_id || this.binding.hmdp_token) ? '\u5df2\u7ed1\u5b9a' : '-')
      }
      return this.binding.sky_take_out_display_name
        || this.binding.sky_take_out_username
        || this.binding.sky_take_out_phone
        || ((this.binding.sky_take_out_user_id || this.binding.sky_take_out_token) ? '\u5df2\u7ed1\u5b9a' : '-')
    },
    async logout() {
      try {
        await axios.get(`${API}/user/logout`, { headers: this.authHeader() })
      } finally {
        localStorage.removeItem('token')
        this.$router.push('/login')
      }
    },
    scrollBottom() {
      this.$nextTick(() => {
        if (this.$refs.chatWindow) {
          this.$refs.chatWindow.scrollTop = this.$refs.chatWindow.scrollHeight
        }
      })
    },
  },
}
</script>

<style scoped>
.agent-page {
  position: relative;
  min-height: 100vh;
  height: 100vh;
  overflow: hidden;
  padding: 18px;
  color: var(--ink-deep);
}

.scene-image,
.scene-veil {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.scene-image {
  background-image:
    linear-gradient(140deg, rgba(18, 33, 26, 0.14), rgba(247, 224, 136, 0.12)),
    var(--scene-backdrop);
  background-size: cover;
  background-position: center;
  transform: scale(1.05);
  filter: blur(16px) saturate(0.98);
  opacity: 0.98;
}

.scene-veil {
  background:
    linear-gradient(180deg, rgba(250, 252, 255, 0.28), rgba(245, 249, 255, 0.18)),
    radial-gradient(circle at 22% 16%, rgba(255, 246, 190, 0.2), transparent 26%);
  backdrop-filter: blur(4px);
}

.chrome-panel {
  position: relative;
  z-index: 1;
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.86), rgba(247, 252, 255, 0.64)),
    linear-gradient(135deg, rgba(78, 212, 255, 0.16), rgba(255, 160, 140, 0.12));
  border: 1px solid rgba(255, 255, 255, 0.74);
  box-shadow:
    0 28px 60px rgba(18, 43, 74, 0.16),
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(20px);
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 16px 18px;
  border-radius: 28px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-mark {
  position: relative;
  width: 54px;
  height: 54px;
  border-radius: 20px;
  background: linear-gradient(145deg, rgba(18, 40, 74, 0.95), rgba(36, 86, 132, 0.88));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12);
}

.brand-mark span {
  position: absolute;
  inset: 11px;
  border-radius: 14px;
  background:
    radial-gradient(circle at 30% 30%, #ffffff 0%, #ffffff 12%, transparent 14%),
    linear-gradient(135deg, #82f2ff 0%, #5fc6ff 45%, #ff9b7d 100%);
  transform: rotate(12deg);
}

.brand-copy h1 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 28px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.brand-meta {
  display: flex;
  gap: 8px;
  margin-top: 6px;
}

.profile-chip,
.status-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.profile-chip {
  background: rgba(255, 255, 255, 0.82);
  color: #244160;
}

.status-chip {
  background: linear-gradient(120deg, #8df4d1 0%, #78f7ff 100%);
  color: #0b3850;
}

.top-actions {
  display: flex;
  gap: 10px;
}

.top-actions button,
.quick-btn,
.composer button,
.settings-panel button {
  border: none;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.top-actions button:hover,
.quick-btn:hover,
.composer button:hover,
.settings-panel button:hover {
  transform: translateY(-1px);
}

.ghost-btn,
.refresh-btn {
  border-radius: 14px;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.74);
  color: #23415f;
  font-weight: 700;
}

.danger-btn {
  border-radius: 14px;
  padding: 10px 16px;
  background: linear-gradient(120deg, #ff9f8f 0%, #ffc58a 100%);
  color: #5a2518;
  font-weight: 700;
}

.console {
  height: calc(100vh - 118px);
  margin-top: 14px;
  border-radius: 32px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.quick-btn {
  min-height: 42px;
  padding: 0 16px;
  border-radius: 16px;
  background:
    linear-gradient(130deg, rgba(255, 255, 255, 0.92), rgba(241, 248, 255, 0.72)),
    linear-gradient(130deg, rgba(104, 225, 255, 0.2), rgba(255, 172, 144, 0.14));
  color: #183a56;
  font-weight: 700;
  box-shadow: 0 10px 24px rgba(27, 62, 92, 0.1);
}

.chat-body {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px;
  border-radius: 26px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.64), rgba(249, 252, 255, 0.42)),
    linear-gradient(135deg, rgba(87, 232, 255, 0.09), rgba(255, 166, 136, 0.08));
  border: 1px solid rgba(255, 255, 255, 0.76);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(6px);
  scrollbar-width: thin;
  scrollbar-color: rgba(47, 92, 130, 0.45) transparent;
}

.chat-body::-webkit-scrollbar {
  width: 8px;
}

.chat-body::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(47, 92, 130, 0.38);
}

.msg {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  margin-bottom: 14px;
}

.msg.user {
  justify-content: flex-end;
}

.msg.user .avatar {
  order: 2;
}

.msg.system {
  justify-content: center;
}

.avatar {
  flex: 0 0 42px;
  width: 42px;
  height: 42px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, rgba(26, 51, 83, 0.94), rgba(53, 105, 155, 0.82));
  color: #f7fbff;
  font-family: var(--font-display);
  font-size: 11px;
  letter-spacing: 0.08em;
}

.bubble {
  position: relative;
  max-width: min(78%, 760px);
  padding: 13px 15px;
  border-radius: 22px;
  white-space: pre-wrap;
  line-height: 1.65;
  font-size: 15px;
  box-shadow: 0 14px 30px rgba(24, 52, 80, 0.08);
}

.msg.user .bubble {
  border-bottom-right-radius: 8px;
  background: linear-gradient(135deg, #1b3454 0%, #2e6ea2 52%, #5dddf6 100%);
  color: #f6fbff;
}

.msg.agent .bubble {
  border-bottom-left-radius: 8px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.94), rgba(240, 249, 255, 0.88));
  color: #1f3d5c;
}

.msg.system .bubble {
  max-width: 420px;
  text-align: center;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.84);
  color: rgba(24, 56, 84, 0.7);
  font-size: 13px;
}

.msg.streaming .bubble::after {
  content: "";
  display: inline-block;
  width: 9px;
  height: 1em;
  margin-left: 5px;
  border-radius: 999px;
  background: currentColor;
  opacity: 0.8;
  vertical-align: -2px;
  animation: blink 0.9s steps(1) infinite;
}

.composer-shell {
  position: relative;
  padding-top: 6px;
}

.quick-actions-pop {
  position: absolute;
  left: 0;
  right: 0;
  bottom: calc(100% + 12px);
  padding: 14px;
  border-radius: 24px;
  transform-origin: bottom center;
}

.quick-actions-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  color: #1f3d5c;
}

.quick-actions-head span {
  font-size: 14px;
  font-weight: 800;
}

.quick-actions-head small {
  color: rgba(31, 61, 92, 0.64);
  font-size: 12px;
}

.quick-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.composer {
  display: grid;
  grid-template-columns: 1fr 120px;
  gap: 12px;
}

.composer input,
.settings-panel input {
  width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: 18px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.78);
  color: #173653;
  outline: none;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.86);
}

.composer input::placeholder,
.settings-panel input::placeholder {
  color: rgba(23, 54, 83, 0.42);
}

.composer input:focus,
.settings-panel input:focus {
  border-color: rgba(102, 213, 255, 0.96);
  box-shadow: 0 0 0 4px rgba(106, 214, 255, 0.16);
}

.send-btn,
.primary-btn {
  border-radius: 18px;
  padding: 0 18px;
  font-weight: 800;
  color: #0b3654;
  background: linear-gradient(120deg, #82f0ff 0%, #ffd18c 100%);
  box-shadow: 0 16px 28px rgba(71, 183, 214, 0.22);
}

.settings-mask {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: flex;
  justify-content: flex-end;
  background: rgba(16, 35, 58, 0.18);
  backdrop-filter: blur(8px);
}

.settings-panel {
  width: min(92vw, 440px);
  height: 100vh;
  padding: 18px;
  overflow-y: auto;
  border-radius: 30px 0 0 30px;
}

.settings-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.settings-head h2,
.settings-card h4 {
  margin: 0;
}

.settings-card {
  margin-top: 14px;
  padding: 14px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(255, 255, 255, 0.74);
}

.settings-card.tokens strong {
  max-width: 210px;
  overflow-wrap: anywhere;
  text-align: right;
}

.setting-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
}

.setting-line:first-child {
  margin-top: 0;
}

.setting-line span {
  color: rgba(23, 54, 83, 0.7);
  font-size: 13px;
}

.setting-line strong {
  color: #173653;
  font-size: 14px;
}

.row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 10px;
}

.settings-card > .primary-btn,
.settings-card > .ghost-btn,
.settings-card > .refresh-btn,
.settings-card > input {
  margin-top: 10px;
}

.binding-tip {
  margin: 10px 0 0;
  color: rgba(23, 54, 83, 0.64);
  font-size: 13px;
  line-height: 1.5;
}

.binding-actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.order-confirm-card {
  margin-top: 12px;
  padding: 12px;
  border-radius: 16px;
  background: rgba(117, 226, 255, 0.1);
  border: 1px solid rgba(121, 208, 234, 0.28);
}

.order-confirm-line,
.order-confirm-items {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-top: 8px;
}

.order-confirm-line:first-child,
.order-confirm-items:first-child {
  margin-top: 0;
}

.order-confirm-line span,
.order-confirm-items > span {
  color: rgba(23, 54, 83, 0.68);
  font-size: 13px;
}

.order-confirm-line strong {
  text-align: right;
  overflow-wrap: anywhere;
}

.order-confirm-items {
  flex-direction: column;
}

.order-confirm-item {
  width: 100%;
  padding: 8px 10px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.72);
  color: #173653;
}

.order-confirm-actions {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.slide-enter-active,
.slide-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
}

.quick-fade-enter-active,
.quick-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.quick-fade-enter-from,
.quick-fade-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.98);
}

@keyframes blink {
  0%,
  49% {
    opacity: 0;
  }
  50%,
  100% {
    opacity: 0.85;
  }
}

@media (max-width: 840px) {
  .agent-page {
    padding: 12px;
  }

  .topbar {
    flex-direction: column;
    align-items: stretch;
  }

  .top-actions {
    justify-content: flex-end;
  }

  .console {
    height: calc(100vh - 146px);
  }
}

@media (max-width: 640px) {
  .brand {
    align-items: flex-start;
  }

  .brand-copy h1 {
    font-size: 22px;
  }

  .quick-actions,
  .composer,
  .row {
    grid-template-columns: 1fr;
  }

  .composer {
    display: grid;
  }

  .bubble {
    max-width: 100%;
  }

  .top-actions {
    width: 100%;
  }

  .top-actions button {
    flex: 1;
  }
}
</style>
