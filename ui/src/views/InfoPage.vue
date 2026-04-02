<template>
  <div class="info-page">
    <div class="panel">
      <h1>系统信息</h1>
      <p>该页面保留为扩展位，核心业务已整合至 Agent 控制台。</p>
      <button @click="$router.push('/agent')">返回控制台</button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'InfoPage'
}
</script>

<style scoped>
.info-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
}

.panel {
  width: min(92vw, 560px);
  padding: 24px;
  border-radius: 16px;
  color: #eaf2ff;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.22);
  backdrop-filter: blur(14px);
}

h1 { margin: 0 0 10px; }
p { margin: 0 0 16px; }

button {
  border: none;
  border-radius: 10px;
  padding: 10px 14px;
  font-weight: 600;
  cursor: pointer;
  background: linear-gradient(120deg, #8ee6ff 0%, #8cf7cf 100%);
  color: #08213a;
}
</style>
