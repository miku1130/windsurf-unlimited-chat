<script setup lang="ts">
// PopupHeader - 复刻寸止标题栏
// 绿色圆点 + 标题 + 主题切换按钮

interface Props {
  currentTheme?: string
  title?: string
}

interface Emits {
  themeChange: [theme: string]
}

const props = withDefaults(defineProps<Props>(), {
  currentTheme: 'light',
  title: '柠檬酱帮你阻止了会话结束',
})

const emit = defineEmits<Emits>()

function handleThemeChange() {
  const nextTheme = props.currentTheme === 'light' ? 'dark' : 'light'
  emit('themeChange', nextTheme)
}
</script>

<template>
  <div class="popup-header" :class="{ dark: currentTheme === 'dark' }">
    <div class="header-left">
      <div class="status-dot"></div>
      <h1 class="header-title">{{ title }}</h1>
    </div>
    <div class="header-right">
      <slot name="extra"></slot>
      <button class="icon-btn" :title="`切换到${currentTheme === 'light' ? '深色' : '浅色'}主题`" @click="handleThemeChange">
        <svg v-if="currentTheme === 'light'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
        <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.popup-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #ffffff;
  border-bottom: 1px solid #e4e7ed;
  user-select: none;
}
.popup-header.dark {
  background: #1e1e1e;
  border-bottom-color: #333;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #52c41a;
  flex-shrink: 0;
}

.header-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin: 0;
}
.dark .header-title {
  color: #e0e0e0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  color: #606266;
  transition: all 0.2s;
}
.icon-btn:hover {
  background: #f0f2f5;
}
.dark .icon-btn {
  color: #aaa;
}
.dark .icon-btn:hover {
  background: #333;
}
</style>
