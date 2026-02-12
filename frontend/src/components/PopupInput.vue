<script setup lang="ts">
// PopupInput - 复刻寸止输入区域
// 预定义选项、图片上传/粘贴、文本输入、快捷模板、上下文追加开关
import type { McpRequest, QuickTemplate, ConstraintToggle } from '../types/popup'
import { NCheckbox, NSwitch, NButton, NImage, NImageGroup, NInput } from 'naive-ui'
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'

interface Props {
  request: McpRequest | null
  loading?: boolean
  submitting?: boolean
  currentTheme?: string
}

interface Emits {
  update: [data: {
    userInput: string
    selectedOptions: string[]
    draggedImages: string[]
  }]
  imageAdd: [image: string]
  imageRemove: [index: number]
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  submitting: false,
  currentTheme: 'light',
})

const emit = defineEmits<Emits>()

// 状态
const userInput = ref('')
const selectedOptions = ref<string[]>([])
const uploadedImages = ref<string[]>([])
const isDragOver = ref(false)

// 快捷模板 (复刻寸止)
const quickTemplates = ref<QuickTemplate[]>([
  { id: 'done', name: 'Done', content: '完成了，可以结束', description: '标记任务完成' },
  { id: 'clear', name: 'Clear', content: '', description: '清空输入框' },
  { id: 'new-issue', name: 'New Issue', content: '这是一个新的问题', description: '提出新问题' },
  { id: 'remember', name: 'Remember', content: '请记住这个信息', description: '记住信息' },
  { id: 'summary-restart', name: 'Summary And Restart', content: '总结并重新开始', description: '总结并重启' },
  { id: 'review-plan', name: 'Review And Plan', content: '回顾并规划下一步', description: '回顾规划' },
])

// 上下文追加开关 (复刻寸止)
const constraintToggles = ref<ConstraintToggle[]>([
  { id: 'no-markdown', label: '不生成Markdown文档', description: '禁止生成总结性Markdown文档', enabled: true },
  { id: 'no-test', label: '不生成测试脚本', description: '禁止生成测试脚本', enabled: true },
  { id: 'no-compile', label: '不编译', description: '禁止编译项目', enabled: true },
  { id: 'no-run', label: '不运行', description: '禁止运行项目', enabled: true },
])

// 计算属性
const hasOptions = computed(() => (props.request?.predefined_options?.length ?? 0) > 0)
const canSubmit = computed(() => {
  const hasOpts = selectedOptions.value.length > 0
  const hasText = userInput.value.trim().length > 0
  const hasImgs = uploadedImages.value.length > 0
  return hasOpts || hasText || hasImgs
})

const statusText = computed(() => {
  if (selectedOptions.value.length > 0 || uploadedImages.value.length > 0 || userInput.value.trim()) {
    return ''
  }
  return '等待输入...'
})

// 发送更新
function emitUpdate() {
  // 构建约束文本
  const constraints = constraintToggles.value
    .filter(t => t.enabled)
    .map(t => t.description)
  const constraintText = constraints.length > 0
    ? '\n\n[约束条件]\n' + constraints.map(c => `- ${c}`).join('\n')
    : ''

  emit('update', {
    userInput: userInput.value + constraintText,
    selectedOptions: selectedOptions.value,
    draggedImages: uploadedImages.value,
  })
}

// 选项切换
function handleOptionToggle(option: string) {
  const idx = selectedOptions.value.indexOf(option)
  if (idx > -1) {
    selectedOptions.value.splice(idx, 1)
  } else {
    selectedOptions.value.push(option)
  }
  emitUpdate()
}

function handleOptionChange(option: string, checked: boolean) {
  if (checked) {
    if (!selectedOptions.value.includes(option)) {
      selectedOptions.value.push(option)
    }
  } else {
    const idx = selectedOptions.value.indexOf(option)
    if (idx > -1) selectedOptions.value.splice(idx, 1)
  }
  emitUpdate()
}

// 文本输入
watch(userInput, () => emitUpdate())

// 快捷模板点击
function handleTemplateClick(template: QuickTemplate) {
  if (template.id === 'clear') {
    userInput.value = ''
  } else {
    userInput.value = template.content
  }
  emitUpdate()
}

// 图片处理
async function handleImageFiles(files: FileList | File[]) {
  for (const file of files) {
    if (file.type.startsWith('image/')) {
      try {
        const base64 = await fileToBase64(file)
        if (!uploadedImages.value.includes(base64)) {
          uploadedImages.value.push(base64)
          emit('imageAdd', base64)
          emitUpdate()
        }
      } catch (e) {
        console.error('图片处理失败:', e)
      }
    }
  }
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      // 去除 data:image/xxx;base64, 前缀
      const base64 = result.split(',')[1] || result
      resolve(base64)
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

function removeImage(index: number) {
  uploadedImages.value.splice(index, 1)
  emit('imageRemove', index)
  emitUpdate()
}

// 拖拽处理
function handleDragOver(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = true
}
function handleDragLeave() {
  isDragOver.value = false
}
function handleDrop(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = false
  if (e.dataTransfer?.files) {
    handleImageFiles(e.dataTransfer.files)
  }
}

// 粘贴处理
function handlePaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  let hasImage = false
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      hasImage = true
      const file = item.getAsFile()
      if (file) handleImageFiles([file])
    }
  }
  if (hasImage) e.preventDefault()
}

// 上传按钮
function triggerUpload() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.multiple = true
  input.onchange = () => {
    if (input.files) handleImageFiles(input.files)
  }
  input.click()
}

// 引用消息
function handleQuoteMessage(message: string) {
  userInput.value = `> ${message.split('\n').join('\n> ')}\n\n`
  emitUpdate()
}

// 键盘监听 - 粘贴
onMounted(() => {
  document.addEventListener('paste', handlePaste as any)
})
onUnmounted(() => {
  document.removeEventListener('paste', handlePaste as any)
})

// 暴露方法
defineExpose({
  canSubmit,
  statusText,
  handleQuoteMessage,
  reset() {
    userInput.value = ''
    selectedOptions.value = []
    uploadedImages.value = []
  },
  updateData(data: any) {
    if (data.selectedOptions) selectedOptions.value = data.selectedOptions
  },
})
</script>

<template>
  <div class="popup-input" :class="{ dark: currentTheme === 'dark' }">
    <!-- 预定义选项 -->
    <div v-if="!loading && hasOptions" class="section">
      <h4 class="section-title">请选择选项</h4>
      <div class="options-list">
        <div
          v-for="(option, index) in request!.predefined_options"
          :key="`option-${index}`"
          class="option-item"
          :class="{ selected: selectedOptions.includes(option) }"
          @click="handleOptionToggle(option)"
        >
          <n-checkbox
            :checked="selectedOptions.includes(option)"
            :disabled="submitting"
            size="medium"
            @update:checked="(checked: boolean) => handleOptionChange(option, checked)"
            @click.stop
          >
            <span class="option-text">{{ option }}</span>
          </n-checkbox>
        </div>
      </div>
    </div>

    <!-- 已添加的图片 -->
    <div v-if="uploadedImages.length > 0" class="section">
      <h4 class="section-title">
        已添加的图片
        <span class="image-count">({{ uploadedImages.length }})</span>
      </h4>
      <div class="image-grid">
        <div
          v-for="(img, index) in uploadedImages"
          :key="`img-${index}`"
          class="image-thumb"
        >
          <img :src="`data:image/png;base64,${img}`" alt="上传图片" />
          <button class="remove-btn" @click="removeImage(index)">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
          <div class="image-index">{{ index + 1 }}</div>
        </div>
      </div>
    </div>

    <!-- 图片拖拽区域 -->
    <div
      class="drop-zone"
      :class="{ 'drag-over': isDragOver }"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop="handleDrop"
    >
      <div class="drop-hint">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>
        </svg>
        <span>拖拽图片到此处，或</span>
        <button class="upload-link" @click="triggerUpload">点击上传</button>
        <span class="drop-sub">支持 Ctrl+V 粘贴</span>
      </div>
    </div>

    <!-- 文本输入 -->
    <div v-if="!loading" class="section">
      <h4 class="section-title">
        {{ hasOptions ? '补充说明 (可选)' : '请输入您的回复' }}
      </h4>
      <n-input
        v-model:value="userInput"
        type="textarea"
        :placeholder="hasOptions ? '在此输入补充说明...' : '在此输入您的回复...'"
        :autosize="{ minRows: 3, maxRows: 8 }"
        :disabled="submitting"
      />
    </div>

    <!-- 快捷模板 -->
    <div v-if="!loading && quickTemplates.length > 0" class="section">
      <div class="template-label">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
        </svg>
        <span>快捷模板:</span>
      </div>
      <div class="template-grid">
        <button
          v-for="tpl in quickTemplates"
          :key="tpl.id"
          class="template-btn"
          :title="tpl.description"
          @click="handleTemplateClick(tpl)"
        >
          {{ tpl.name }}
        </button>
      </div>
    </div>

    <!-- 上下文追加 (条件性开关) -->
    <div v-if="!loading && constraintToggles.length > 0" class="section">
      <div class="template-label">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>
        <span>上下文追加:</span>
      </div>
      <div class="constraint-grid">
        <div
          v-for="toggle in constraintToggles"
          :key="toggle.id"
          class="constraint-item"
        >
          <div class="constraint-info">
            <span class="constraint-label">{{ toggle.label }}</span>
          </div>
          <n-switch
            v-model:value="toggle.enabled"
            size="small"
            @update:value="emitUpdate"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.popup-input {
  padding: 0;
}

.section {
  margin-bottom: 16px;
}

.section-title {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  margin: 0 0 8px;
}
.dark .section-title {
  color: #e0e0e0;
}

.image-count {
  font-weight: 400;
  color: #909399;
  font-size: 12px;
}

/* 选项列表 */
.options-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.option-item {
  padding: 10px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fafafa;
}
.option-item:hover {
  border-color: #1890ff;
  background: #e6f7ff;
}
.option-item.selected {
  border-color: #1890ff;
  background: #e6f7ff;
}
.dark .option-item {
  background: #2a2a2a;
  border-color: #444;
}
.dark .option-item:hover,
.dark .option-item.selected {
  border-color: #1890ff;
  background: #1a3a5c;
}
.option-text {
  font-size: 13px;
  color: #303133;
}
.dark .option-text {
  color: #e0e0e0;
}

/* 图片网格 */
.image-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.image-thumb {
  position: relative;
  width: 80px;
  height: 80px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #e4e7ed;
}
.dark .image-thumb {
  border-color: #444;
}
.image-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.remove-btn {
  position: absolute;
  top: -1px;
  right: -1px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ff4d4f;
  border: none;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 2;
}
.image-index {
  position: absolute;
  bottom: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #1890ff;
  color: white;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}

/* 拖拽区域 */
.drop-zone {
  border: 1px dashed #d9d9d9;
  border-radius: 8px;
  padding: 12px;
  text-align: center;
  transition: all 0.2s;
  margin-bottom: 16px;
}
.drop-zone.drag-over {
  border-color: #1890ff;
  background: #e6f7ff;
}
.dark .drop-zone {
  border-color: #444;
}
.dark .drop-zone.drag-over {
  border-color: #1890ff;
  background: #1a3a5c;
}
.drop-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12px;
  color: #909399;
  flex-wrap: wrap;
}
.upload-link {
  background: none;
  border: none;
  color: #1890ff;
  cursor: pointer;
  font-size: 12px;
  padding: 0;
}
.upload-link:hover {
  text-decoration: underline;
}
.drop-sub {
  width: 100%;
  font-size: 11px;
  color: #c0c4cc;
  margin-top: 2px;
}

/* 快捷模板 */
.template-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #909399;
  margin-bottom: 8px;
}
.dark .template-label {
  color: #777;
}
.template-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.template-btn {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  font-size: 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: #fafafa;
  color: #303133;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}
.template-btn:hover {
  border-color: #1890ff;
  color: #1890ff;
  background: #e6f7ff;
}
.dark .template-btn {
  background: #2a2a2a;
  border-color: #444;
  color: #e0e0e0;
}
.dark .template-btn:hover {
  border-color: #1890ff;
  color: #1890ff;
  background: #1a3a5c;
}

/* 上下文追加 */
.constraint-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.constraint-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #fafafa;
}
.dark .constraint-item {
  background: #2a2a2a;
  border-color: #444;
}
.constraint-label {
  font-size: 12px;
  color: #303133;
}
.dark .constraint-label {
  color: #e0e0e0;
}
</style>
