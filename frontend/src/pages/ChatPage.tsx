import { useEffect, useRef, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useChatStore, Message } from '../stores/chat'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { 
  Send, 
  Bot, 
  User, 
  Loader2, 
  Sparkles,
  Code,
  FileText,
  Zap,
  AlertCircle,
  Copy,
  Check,
  RefreshCw,
  StopCircle,
  Terminal,
  ChevronDown,
  ChevronRight
} from 'lucide-react'
import clsx from 'clsx'

export default function ChatPage() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const [input, setInput] = useState('')
  
  const {
    currentSessionId,
    sessionMessages,
    isLoadingMessages,
    isSending,
    currentPhase,
    error,
    selectSession,
    createSession,
    sendMessage,
    clearError,
    getCurrentSession,
    getSessionMessages
  } = useChatStore()

  const currentSession = getCurrentSession()
  const messages = sessionId ? getSessionMessages(sessionId) : []

  // Load session when sessionId changes
  useEffect(() => {
    if (sessionId && sessionId !== currentSessionId) {
      selectSession(sessionId)
    }
  }, [sessionId, currentSessionId, selectSession])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input on load
  useEffect(() => {
    inputRef.current?.focus()
  }, [currentSession])

  // Auto-resize textarea
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px'
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isSending) return

    const message = input.trim()
    setInput('')
    
    // Reset textarea height
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
    }

    // Create session if needed
    if (!sessionId) {
      try {
        const session = await createSession()
        navigate(`/chat/${session.id}`, { replace: true })
        // Small delay to ensure navigation completes
        setTimeout(() => sendMessage(message), 100)
        return
      } catch {
        return
      }
    }

    sendMessage(message)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="flex flex-col h-full bg-bg-primary">
      {/* Header */}
      <header className="flex-shrink-0 px-6 py-4 border-b border-border-default bg-bg-secondary/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-blue/20 to-accent-purple/20 flex items-center justify-center border border-accent-blue/20">
              <Bot className="w-5 h-5 text-accent-blue" />
            </div>
            <div>
              <h2 className="font-medium text-text-primary">
                {currentSession?.title || 'New Conversation'}
              </h2>
              <p className="text-xs text-text-secondary">
                {currentSession?.model_name || 'gpt-3.5-turbo'} • {messages.length} messages
              </p>
            </div>
          </div>
          
          {/* Phase Indicator */}
          {currentPhase && (
            <PhaseIndicator phase={currentPhase} />
          )}
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {isLoadingMessages ? (
          <LoadingState />
        ) : messages.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
            {messages.map((message, index) => (
              <MessageBubble 
                key={message.id} 
                message={message} 
                isLast={index === messages.length - 1}
              />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Error Toast */}
      {error && (
        <div className="px-4 py-3 mx-4 mb-4 rounded-xl bg-accent-red/10 border border-accent-red/30 text-accent-red text-sm flex items-center gap-3 animate-slide-up max-w-4xl self-center">
          <AlertCircle size={18} className="flex-shrink-0" />
          <span className="flex-1">{error}</span>
          <button 
            onClick={clearError} 
            className="text-xs font-medium hover:underline flex-shrink-0"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Input */}
      <div className="flex-shrink-0 px-4 py-4 border-t border-border-default bg-bg-secondary/80 backdrop-blur-sm">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
          <div className="relative flex items-end gap-3 p-3 rounded-2xl bg-bg-tertiary border border-border-default focus-within:border-accent-blue/50 focus-within:shadow-lg focus-within:shadow-accent-blue/5 transition-all">
            <textarea
              ref={inputRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Type your message... (Shift+Enter for new line)"
              rows={1}
              className="flex-1 bg-transparent resize-none outline-none text-text-primary placeholder:text-text-tertiary min-h-[24px] max-h-[200px] leading-relaxed"
              disabled={isSending}
            />
            <button
              type="submit"
              disabled={!input.trim() || isSending}
              className={clsx(
                'flex-shrink-0 p-2.5 rounded-xl transition-all duration-200',
                input.trim() && !isSending
                  ? 'bg-gradient-to-r from-accent-blue to-accent-purple text-white shadow-lg shadow-accent-blue/20 hover:shadow-xl hover:shadow-accent-blue/30'
                  : 'bg-bg-elevated text-text-tertiary cursor-not-allowed'
              )}
            >
              {isSending ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
          <p className="text-xs text-text-tertiary text-center mt-3">
            Agent Bot can make mistakes. Verify important information.
          </p>
        </form>
      </div>
    </div>
  )
}

function PhaseIndicator({ phase }: { phase: string }) {
  const phaseConfig: Record<string, { label: string; color: string }> = {
    thinking: { label: 'Thinking...', color: 'accent-blue' },
    planning: { label: 'Planning...', color: 'accent-purple' },
    executing: { label: 'Executing...', color: 'accent-yellow' },
    summarizing: { label: 'Summarizing...', color: 'accent-green' },
    responding: { label: 'Responding...', color: 'accent-cyan' }
  }
  
  const config = phaseConfig[phase] || { label: phase, color: 'accent-blue' }
  
  return (
    <div className={clsx(
      'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium',
      `bg-${config.color}/10 text-${config.color} border border-${config.color}/30`
    )}>
      <Sparkles size={14} className="animate-pulse" />
      <span>{config.label}</span>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <div className="relative">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent-blue/20 to-accent-purple/20 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-accent-blue" />
        </div>
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-accent-blue to-accent-purple opacity-20 blur-xl animate-pulse" />
      </div>
      <p className="text-text-secondary">Loading conversation...</p>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-4">
      <div className="relative mb-8">
        <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-accent-blue/20 to-accent-purple/20 flex items-center justify-center border border-accent-blue/20">
          <Zap className="w-12 h-12 text-accent-blue" />
        </div>
        <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-accent-blue to-accent-purple opacity-10 blur-2xl" />
      </div>
      
      <h2 className="text-2xl font-display font-bold mb-3 gradient-text">
        How can I help you today?
      </h2>
      <p className="text-text-secondary mb-8 max-w-md">
        I can help you with coding tasks, analyze code, explore projects, and much more. Just type your question below.
      </p>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg w-full">
        <SuggestionCard
          icon={<Code className="w-5 h-5" />}
          title="Code Analysis"
          description="Analyze and explain code structure"
        />
        <SuggestionCard
          icon={<FileText className="w-5 h-5" />}
          title="File Operations"
          description="Read, write, and edit files"
        />
      </div>
    </div>
  )
}

function SuggestionCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="p-4 rounded-xl bg-bg-secondary border border-border-default hover:border-accent-blue/30 hover:bg-bg-tertiary cursor-pointer transition-all group">
      <div className="flex items-start gap-3">
        <div className="p-2.5 rounded-lg bg-accent-blue/10 text-accent-blue group-hover:bg-accent-blue/20 transition-colors">
          {icon}
        </div>
        <div className="text-left">
          <h3 className="font-medium text-sm text-text-primary">{title}</h3>
          <p className="text-xs text-text-secondary mt-0.5">{description}</p>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ message, isLast }: { message: Message; isLast: boolean }) {
  const isUser = message.role === 'user'
  const isTool = message.role === 'tool'
  const isStreaming = message.isStreaming
  const [copied, setCopied] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Handle Tool Output
  if (isTool) {
    return (
      <div className="flex gap-4 animate-slide-up">
        <div className="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center bg-bg-tertiary border border-border-default">
          <Terminal size={18} className="text-accent-yellow" />
        </div>
        <div className="flex-1 max-w-[85%]">
          <div 
            className="rounded-xl border border-border-default bg-bg-tertiary overflow-hidden"
          >
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-text-secondary hover:bg-bg-elevated transition-colors"
            >
              {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              <span>Tool Output</span>
              <span className="ml-auto font-mono text-[10px] opacity-50">{message.tool_call_id}</span>
            </button>
            {isExpanded && (
              <div className="px-3 py-2 border-t border-border-default bg-bg-elevated overflow-x-auto">
                <pre className="text-xs font-mono text-text-secondary whitespace-pre-wrap">
                  {message.content}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div
      className={clsx(
        'flex gap-4 animate-slide-up',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div
        className={clsx(
          'flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center shadow-md',
          isUser
            ? 'bg-gradient-to-br from-accent-purple to-accent-cyan'
            : 'bg-gradient-to-br from-accent-blue to-accent-purple'
        )}
      >
        {isUser ? <User size={18} className="text-white" /> : <Bot size={18} className="text-white" />}
      </div>

      {/* Content */}
      <div className="flex-1 max-w-[85%] space-y-2">
        {/* Tool Calls */}
        {message.tool_calls && Array.isArray(message.tool_calls) && message.tool_calls.map((toolCall: any, idx) => (
          <div key={idx} className="rounded-xl border border-accent-yellow/30 bg-accent-yellow/5 overflow-hidden">
            <div className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-accent-yellow">
              <Terminal size={14} />
              <span>Calling Tool: {toolCall.function?.name}</span>
            </div>
            <div className="px-3 py-2 border-t border-accent-yellow/10 bg-accent-yellow/5 font-mono text-xs text-text-secondary whitespace-pre-wrap">
              {toolCall.function?.arguments}
            </div>
          </div>
        ))}

        <div
          className={clsx(
            'group relative rounded-2xl px-4 py-3',
            isUser
              ? 'bg-gradient-to-br from-accent-purple/10 to-accent-cyan/10 border border-accent-purple/20'
              : 'bg-bg-secondary border border-border-default'
          )}
        >
          {/* Copy button for assistant messages */}
          {!isUser && message.content && (
            <button
              onClick={handleCopy}
              className="absolute top-2 right-2 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 bg-bg-tertiary hover:bg-bg-elevated transition-all"
              title="Copy message"
            >
              {copied ? (
                <Check size={14} className="text-accent-green" />
              ) : (
                <Copy size={14} className="text-text-tertiary" />
              )}
            </button>
          )}
          
          {isUser ? (
            <p className="whitespace-pre-wrap text-text-primary leading-relaxed">{message.content}</p>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown
                components={{
                  code({ node, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '')
                    const isInline = !match
                    
                    return isInline ? (
                      <code className="bg-bg-elevated px-1.5 py-0.5 rounded text-accent-cyan text-sm font-mono" {...props}>
                        {children}
                      </code>
                    ) : (
                      <div className="relative group/code">
                        <SyntaxHighlighter
                          style={oneDark}
                          language={match[1]}
                          PreTag="div"
                          className="rounded-xl !bg-bg-elevated !my-4 text-sm"
                          customStyle={{
                            padding: '1rem',
                            borderRadius: '0.75rem',
                            border: '1px solid var(--border-default)'
                          }}
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      </div>
                    )
                  },
                  p({ children }) {
                    return <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>
                  },
                  ul({ children }) {
                    return <ul className="list-disc list-inside mb-3 space-y-1">{children}</ul>
                  },
                  ol({ children }) {
                    return <ol className="list-decimal list-inside mb-3 space-y-1">{children}</ol>
                  },
                  h1({ children }) {
                    return <h1 className="text-xl font-bold mb-3 mt-4 first:mt-0">{children}</h1>
                  },
                  h2({ children }) {
                    return <h2 className="text-lg font-bold mb-2 mt-4 first:mt-0">{children}</h2>
                  },
                  h3({ children }) {
                    return <h3 className="text-base font-bold mb-2 mt-3 first:mt-0">{children}</h3>
                  }
                }}
              >
                {message.content || ' '}
              </ReactMarkdown>
              
              {isStreaming && (
                <span className="typing-indicator ml-1">
                  <span></span>
                  <span></span>
                  <span></span>
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
