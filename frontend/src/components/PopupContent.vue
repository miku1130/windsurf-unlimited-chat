<script setup lang="ts">
// PopupContent - 复刻寸止消息内容区域
// 支持 Markdown 渲染、引用、代码高亮
import type { McpRequest } from '../types/popup'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import { computed, ref, watch, onMounted, nextTick } from 'vue'

interface Props {
  request: McpRequest | null
  loading?: boolean
  currentTheme?: string
}

interface Emits {
  quoteMessage: [message: string]
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  currentTheme: 'light',
})

const emit = defineEmits<Emits>()
const showQuote = ref(false)

// Markdown 渲染器
const md: MarkdownIt = new MarkdownIt({
  html: true,
  breaks: true,
  linkify: true,
  highlight: (str: string, lang: string): string => {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class="hljs"><code>${hljs.highlight(str, { language: lang }).value}</code></pre>`
      } catch (_) {
        // ignore
      }
    }
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`
  },
})

const renderedContent = computed(() => {
  if (!props.request?.message) return ''
  if (props.request.is_markdown) {
    return md.render(props.request.message)
  }
  return `<p>${props.request.message.replace(/\n/g, '<br>')}</p>`
})

function handleQuote() {
  if (props.request?.message) {
    emit('quoteMessage', props.request.message)
  }
}

// 代码块复制按钮
function setupCopyButtons() {
  nextTick(() => {
    setTimeout(() => {
      const preElements = document.querySelectorAll('.markdown-content pre')
      preElements.forEach((pre) => {
        if (pre.querySelector('.copy-btn')) return
        const btn = document.createElement('button')
        btn.className = 'copy-btn'
        btn.textContent = '复制'
        btn.addEventListener('click', async () => {
          const code = pre.querySelector('code')
          if (code) {
            try {
              await navigator.clipboard.writeText(code.textContent || '')
              btn.textContent = '已复制'
              setTimeout(() => { btn.textContent = '复制' }, 2000)
            } catch (e) {
              console.error('复制失败:', e)
            }
          }
        })
        ;(pre as HTMLElement).style.position = 'relative'
        pre.appendChild(btn)
      })
    }, 100)
  })
}

watch(() => props.request, () => {
  if (props.request) setupCopyButtons()
}, { deep: true })

onMounted(() => {
  if (props.request) setupCopyButtons()
})
</script>

<template>
  <div class="popup-content" :class="{ dark: currentTheme === 'dark' }">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <!-- 消息内容 -->
    <div v-else-if="request?.message" class="message-area">
      <!-- Markdown 渲染 -->
      <div
        v-if="request.is_markdown"
        class="markdown-content"
        v-html="renderedContent"
      ></div>
      <!-- 纯文本 -->
      <div v-else class="plain-content" v-html="renderedContent"></div>

      <!-- 引用按钮 -->
      <div class="quote-bar">
        <button class="quote-btn" @click="handleQuote">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          引用原文
        </button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <p>等待消息...</p>
    </div>
  </div>
</template>

<style scoped>
.popup-content {
  padding: 0;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  color: #909399;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid #e4e7ed;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.message-area {
  position: relative;
}

.markdown-content {
  font-size: 13px;
  line-height: 1.7;
  color: #303133;
  word-break: break-word;
}
.dark .markdown-content {
  color: #e0e0e0;
}

.markdown-content :deep(h1) { font-size: 1.25em; font-weight: 700; margin: 16px 0 8px; }
.markdown-content :deep(h2) { font-size: 1.1em; font-weight: 600; margin: 14px 0 6px; }
.markdown-content :deep(h3) { font-size: 1em; font-weight: 600; margin: 12px 0 4px; }
.markdown-content :deep(p) { margin: 6px 0; }
.markdown-content :deep(ul), .markdown-content :deep(ol) { padding-left: 20px; margin: 6px 0; }
.markdown-content :deep(li) { margin: 2px 0; }
.markdown-content :deep(code) {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.9em;
  font-family: 'Cascadia Code', 'Fira Code', Consolas, monospace;
}
.dark .markdown-content :deep(code) {
  background: #2d2d2d;
}
.markdown-content :deep(pre) {
  background: #f8f8f8;
  border-radius: 8px;
  padding: 12px 16px;
  overflow-x: auto;
  margin: 8px 0;
  position: relative;
}
.dark .markdown-content :deep(pre) {
  background: #1a1a1a;
}
.markdown-content :deep(pre code) {
  background: none;
  padding: 0;
}
.markdown-content :deep(blockquote) {
  border-left: 3px solid #1890ff;
  padding: 8px 12px;
  margin: 8px 0;
  color: #606266;
  background: #f9f9f9;
}
.dark .markdown-content :deep(blockquote) {
  color: #aaa;
  background: #252525;
}
.markdown-content :deep(a) {
  color: #1890ff;
  text-decoration: none;
}
.markdown-content :deep(a:hover) {
  text-decoration: underline;
}
.markdown-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
}
.markdown-content :deep(th), .markdown-content :deep(td) {
  border: 1px solid #e4e7ed;
  padding: 6px 10px;
  text-align: left;
}
.dark .markdown-content :deep(th), .dark .markdown-content :deep(td) {
  border-color: #444;
}

.plain-content {
  font-size: 13px;
  line-height: 1.7;
  color: #303133;
}
.dark .plain-content {
  color: #e0e0e0;
}

.quote-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}
.dark .quote-bar {
  border-top-color: #333;
}

.quote-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #909399;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
}
.quote-btn:hover {
  color: #1890ff;
  background: #e6f7ff;
}
.dark .quote-btn:hover {
  background: #1a3a5c;
}

.empty-state {
  text-align: center;
  padding: 32px;
  color: #c0c4cc;
}

/* 代码复制按钮 */
:deep(.copy-btn) {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 11px;
  padding: 2px 8px;
  background: rgba(255,255,255,0.8);
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  color: #666;
  transition: all 0.2s;
}
:deep(.copy-btn:hover) {
  background: #fff;
  color: #1890ff;
  border-color: #1890ff;
}
.dark :deep(.copy-btn) {
  background: rgba(50,50,50,0.8);
  border-color: #555;
  color: #aaa;
}
.dark :deep(.copy-btn:hover) {
  background: #444;
  color: #1890ff;
}
</style>
