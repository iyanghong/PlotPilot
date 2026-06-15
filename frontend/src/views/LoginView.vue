<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <h1>PlotPilot</h1>
        <p>墨枢 — AI 小说创作平台</p>
      </div>

      <n-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-placement="top"
      >
        <n-form-item path="username" label="用户名">
          <n-input
            v-model:value="form.username"
            placeholder="请输入用户名"
            size="large"
            :disabled="submitting"
          />
        </n-form-item>

        <n-form-item path="password" label="密码">
          <n-input
            v-model:value="form.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            :disabled="submitting"
            @keyup.enter="handleSubmit"
          />
        </n-form-item>

        <n-form-item>
          <n-checkbox v-model:checked="rememberPwd">
            记住密码
          </n-checkbox>
        </n-form-item>

        <n-button
          type="primary"
          size="large"
          block
          :loading="submitting"
          @click="handleSubmit"
        >
          登录
        </n-button>
      </n-form>

      <n-alert
        v-if="errorMsg"
        type="error"
        :title="errorMsg"
        closable
        class="login-error"
        @close="errorMsg = ''"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NForm, NFormItem, NInput, NButton, NCheckbox, NAlert } from 'naive-ui'
import type { FormInst, FormRules } from 'naive-ui'
import { useAuthStore } from '@/stores/authStore'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref<FormInst | null>(null)
const submitting = ref(false)
const errorMsg = ref('')
const rememberPwd = ref(false)

const REMEMBER_KEY = 'plotpilot_remembered_login'

// 页面加载时恢复已保存的账号密码
onMounted(() => {
  try {
    const saved = localStorage.getItem(REMEMBER_KEY)
    if (saved) {
      const data = JSON.parse(saved)
      if (data.username && data.password) {
        form.username = data.username
        form.password = data.password
        rememberPwd.value = true
      }
    }
  } catch {
    // 解析失败则忽略
  }
})

const form = reactive({
  username: '',
  password: '',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleSubmit() {
  errorMsg.value = ''
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    const result = await authStore.login(form.username, form.password)
    if (result.success) {
      // 记住密码
      if (rememberPwd.value) {
        localStorage.setItem(REMEMBER_KEY, JSON.stringify({
          username: form.username,
          password: form.password,
        }))
      } else {
        localStorage.removeItem(REMEMBER_KEY)
      }
      const redirect = (route.query.redirect as string) || '/'
      router.push(redirect)
    } else {
      errorMsg.value = result.error || '登录失败，请检查用户名和密码'
    }
  } catch {
    errorMsg.value = '网络错误，请检查后端服务是否运行'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
  max-width: 90vw;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 8px;
}

.login-header p {
  font-size: 14px;
  color: #888;
  margin: 0;
}

.login-error {
  margin-top: 16px;
}
</style>
