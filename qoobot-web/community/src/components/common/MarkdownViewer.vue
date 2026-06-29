<template>
  <div class="markdown-viewer" v-html="renderedHtml"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

const md = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
  highlight(str: string, lang: string) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre><code class="hljs language-${lang}">${hljs.highlight(str, { language: lang }).value}</code></pre>`
      } catch {}
    }
    return `<pre><code class="hljs">${md.utils.escapeHtml(str)}</code></pre>`
  }
})

const props = defineProps<{
  content: string
}>()

const renderedHtml = computed(() => md.render(props.content || ''))
</script>

<style lang="scss" scoped>
.markdown-viewer {
  line-height: 1.8;
  font-size: 15px;
  color: var(--qoo-text);

  :deep(h1) { font-size: 28px; margin: 24px 0 16px; }
  :deep(h2) { font-size: 22px; margin: 20px 0 12px; }
  :deep(h3) { font-size: 18px; margin: 16px 0 8px; }
  :deep(p) { margin-bottom: 12px; }
  :deep(code) {
    background: #f5f5f5;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 13px;
  }
  :deep(pre) {
    background: #f5f5f5;
    padding: 16px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 12px 0;

    code { background: none; padding: 0; }
  }
  :deep(blockquote) {
    border-left: 4px solid var(--qoo-primary);
    padding-left: 16px;
    margin: 12px 0;
    color: var(--qoo-text-secondary);
  }
  :deep(img) {
    max-width: 100%;
    border-radius: 8px;
  }
  :deep(a) {
    color: var(--qoo-primary);
  }
}
</style>
