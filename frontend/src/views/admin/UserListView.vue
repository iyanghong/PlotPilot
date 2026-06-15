<!-- UserListView.vue — 用户管理页 — 作者：Axelton -->
<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NCard, NDataTable, NButton, NModal, NForm, NFormItem, NInput, NSelect, NSpace, NPopconfirm, NTag, useMessage } from 'naive-ui'
import { adminApi, type UserDTO } from '@/api/admin'

const message = useMessage()
const users = ref<UserDTO[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)

const showCreate = ref(false)
const newUser = ref({ username: '', password: '', role: 'user' })

// ── 编辑用户 ──
const showEdit = ref(false)
const editUser = ref<{ id: string; username: string; role: string; newPassword: string }>({
  id: '',
  username: '',
  role: 'user',
  newPassword: '',
})

function openEdit(row: UserDTO) {
  editUser.value = { id: row.id, username: row.username, role: row.role, newPassword: '' }
  showEdit.value = true
}

async function saveEdit() {
  try {
    const body: { role?: string; password?: string } = { role: editUser.value.role }
    if (editUser.value.newPassword) {
      body.password = editUser.value.newPassword
    }
    await adminApi.updateUser(editUser.value.id, body)
    message.success('用户已更新')
    showEdit.value = false
    loadUsers()
  } catch (e: any) { message.error('更新失败: ' + (e.response?.data?.detail || e.message)) }
}

const columns = [
  { title: '用户名', key: 'username' },
  {
    title: '角色', key: 'role',
    render(row: UserDTO) {
      return h(NTag, { type: row.role === 'admin' ? 'error' : 'info', size: 'small' }, { default: () => row.role === 'admin' ? '管理员' : '用户' })
    },
  },
  {
    title: '操作', key: 'actions',
    render(row: UserDTO) {
      return h(NSpace, null, {
        default: () => [
          h(NButton, { size: 'small', text: true, type: 'primary', onClick: () => openEdit(row) }, { default: () => '编辑' }),
          h(NPopconfirm, { onPositiveClick: () => deleteUser(row.id) }, {
            default: () => '确认删除该用户？',
            trigger: () => h(NButton, { size: 'small', type: 'error', text: true }, { default: () => '删除' }),
          }),
        ],
      })
    },
  },
]

async function loadUsers() {
  loading.value = true
  try {
    const res = await adminApi.listUsers({ page: page.value, page_size: 20 })
    users.value = res.data
    total.value = res.total
  } catch (e: any) {
    message.error('加载用户列表失败')
  } finally { loading.value = false }
}

async function createUser() {
  try {
    await adminApi.createUser(newUser.value)
    message.success('用户创建成功')
    showCreate.value = false
    newUser.value = { username: '', password: '', role: 'user' }
    loadUsers()
  } catch (e: any) { message.error('创建失败: ' + (e.response?.data?.detail || e.message)) }
}

async function deleteUser(userId: string) {
  try {
    await adminApi.deleteUser(userId)
    message.success('用户已删除')
    loadUsers()
  } catch (e: any) { message.error('删除失败') }
}

onMounted(loadUsers)
</script>

<template>
  <div>
    <n-space justify="space-between" style="margin-bottom:16px">
      <h2 style="margin:0">用户管理</h2>
      <n-button type="primary" @click="showCreate = true">新建用户</n-button>
    </n-space>

    <n-card>
      <n-dataTable :columns="columns" :data="users" :loading="loading"
        :pagination="{ page: page, pageSize: 20, itemCount: total }" />
    </n-card>

    <!-- 创建用户弹窗 -->
    <n-modal v-model:show="showCreate" title="新建用户" preset="card" style="width:420px">
      <n-form :model="newUser" label-placement="left" label-width="80">
        <n-form-item label="用户名"><n-input v-model:value="newUser.username" /></n-form-item>
        <n-form-item label="密码"><n-input v-model:value="newUser.password" type="password" /></n-form-item>
        <n-form-item label="角色">
          <n-select v-model:value="newUser.role" :options="[{ label:'用户', value:'user' }, { label:'管理员', value:'admin' }]" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showCreate = false">取消</n-button>
          <n-button type="primary" @click="createUser">创建</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 编辑用户弹窗 -->
    <n-modal v-model:show="showEdit" title="编辑用户" preset="card" style="width:420px">
      <n-form :model="editUser" label-placement="left" label-width="80">
        <n-form-item label="用户名">
          <n-input :value="editUser.username" disabled />
        </n-form-item>
        <n-form-item label="角色">
          <n-select v-model:value="editUser.role" :options="[{ label:'用户', value:'user' }, { label:'管理员', value:'admin' }]" />
        </n-form-item>
        <n-form-item label="新密码">
          <n-input v-model:value="editUser.newPassword" type="password" placeholder="留空则不修改密码" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showEdit = false">取消</n-button>
          <n-button type="primary" @click="saveEdit">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>
