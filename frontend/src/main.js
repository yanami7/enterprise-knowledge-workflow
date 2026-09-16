import { createApp, onMounted, ref } from 'vue/dist/vue.esm-bundler.js'
import './style.css'

const API = ''

const App = {
  setup() {
    const question = ref('公司 VPN 连接不上，应该怎么处理？')
    const loading = ref(false)
    const answer = ref(null)
    const metrics = ref({ query_count: 0, pending_action_count: 0, ticket_count: 0, document_count: 0 })
    const knowledge = ref([])
    const tickets = ref([])
    const health = ref({ status: 'loading', database: '-', cache: '-' })
    const message = ref('')

    async function getJson(path, options) {
      const response = await fetch(`${API}${path}`, options)
      if (!response.ok) throw new Error((await response.json()).detail || '请求失败')
      return response.json()
    }

    async function refresh() {
      const [metricData, knowledgeData, ticketData, healthData] = await Promise.all([
        getJson('/api/dashboard'),
        getJson('/api/knowledge'),
        getJson('/api/tickets'),
        getJson('/health'),
      ])
      metrics.value = metricData
      knowledge.value = knowledgeData
      tickets.value = ticketData
      health.value = healthData
    }

    async function ask() {
      if (!question.value.trim()) return
      loading.value = true
      message.value = ''
      try {
        answer.value = await getJson('/api/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: question.value }),
        })
        await refresh()
      } catch (error) {
        message.value = error.message
      } finally {
        loading.value = false
      }
    }

    async function decide(action, decision) {
      try {
        await getJson(`/api/actions/${action.id}/${decision}`, { method: 'POST' })
        message.value = decision === 'approve' ? '操作已确认，IT 支持工单已创建。' : '操作已驳回，未执行任何变更。'
        answer.value.pending_action = null
        await refresh()
      } catch (error) {
        message.value = error.message
      }
    }

    onMounted(refresh)
    return { question, loading, answer, metrics, knowledge, tickets, health, message, ask, decide }
  },
  template: `
    <div class="shell">
      <aside class="sidebar">
        <div class="brand"><span class="brand-mark">K</span><div><strong>KnowledgeFlow</strong><small>企业信息化工作台</small></div></div>
        <nav>
          <a class="active" href="#assistant">知识助手</a>
          <a href="#knowledge">知识库</a>
          <a href="#tickets">工单记录</a>
        </nav>
        <div class="system-state">
          <span :class="['dot', health.status]"></span>
          <div><strong>服务 {{ health.status === 'ok' ? '运行正常' : '连接中' }}</strong><small>DB {{ health.database }} · Cache {{ health.cache }}</small></div>
        </div>
      </aside>

      <main>
        <header><div><p class="eyebrow">INFORMATION OPERATIONS</p><h1>企业知识与流程协同平台</h1><p>让制度查询、IT 支持与执行审批形成可追溯闭环。</p></div><span class="version">MVP 1.0</span></header>

        <section class="metrics">
          <article><span>累计问答</span><strong>{{ metrics.query_count }}</strong><small>已记录请求</small></article>
          <article><span>待审批操作</span><strong>{{ metrics.pending_action_count }}</strong><small>人工确认后执行</small></article>
          <article><span>支持工单</span><strong>{{ metrics.ticket_count }}</strong><small>流程闭环记录</small></article>
          <article><span>知识文档</span><strong>{{ metrics.document_count }}</strong><small>当前索引数量</small></article>
        </section>

        <section id="assistant" class="panel assistant">
          <div class="panel-title"><div><span>智能工作台</span><h2>先检索依据，再执行操作</h2></div><span class="tag">Human in the loop</span></div>
          <div class="composer">
            <textarea v-model="question" @keydown.ctrl.enter="ask" placeholder="例如：业务系统无法登录，帮我创建支持工单"></textarea>
            <button @click="ask" :disabled="loading">{{ loading ? '处理中…' : '提交问题' }}</button>
          </div>
          <p class="hint">Ctrl + Enter 快速提交 · 涉及工单创建时必须人工确认</p>

          <div v-if="answer" class="answer">
            <div class="answer-head"><span>处理结果</span><span class="route">{{ answer.route }}</span></div>
            <p>{{ answer.answer }}</p>
            <div v-if="answer.citations.length" class="citations">
              <strong>参考依据</strong>
              <span v-for="item in answer.citations" :key="item.source">{{ item.title }} · {{ item.source }} · {{ item.score }}</span>
            </div>
            <div v-if="answer.pending_action" class="approval">
              <div><strong>需要人工确认</strong><p>{{ answer.pending_action.summary }}</p></div>
              <div><button class="ghost" @click="decide(answer.pending_action, 'reject')">驳回</button><button @click="decide(answer.pending_action, 'approve')">确认并创建工单</button></div>
            </div>
          </div>
          <p v-if="message" class="message">{{ message }}</p>
        </section>

        <div class="grid">
          <section id="knowledge" class="panel">
            <div class="panel-title"><div><span>KNOWLEDGE BASE</span><h2>已索引文档</h2></div></div>
            <div class="list"><article v-for="item in knowledge" :key="item.source"><span class="file">MD</span><div><strong>{{ item.title }}</strong><small>{{ item.source }}</small></div></article></div>
          </section>
          <section id="tickets" class="panel">
            <div class="panel-title"><div><span>AUDIT TRAIL</span><h2>最近工单</h2></div></div>
            <div v-if="tickets.length" class="list"><article v-for="item in tickets" :key="item.id"><span class="ticket">#{{ item.id }}</span><div><strong>{{ item.description }}</strong><small>{{ item.status }} · {{ new Date(item.created_at).toLocaleString() }}</small></div></article></div>
            <p v-else class="empty">暂无工单。提交带有“报修、故障或申请”的问题即可体验审批流程。</p>
          </section>
        </div>
      </main>
    </div>
  `,
}

createApp(App).mount('#app')

