import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '../lib/api'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  tool_call_id?: string
  tool_calls?: unknown[]
  created_at: string
  isStreaming?: boolean
}

export interface Session {
  id: string
  title: string
  description?: string
  model_name: string
  is_archived: boolean
  is_pinned: boolean
  tags: string[]
  total_tokens_used: number
  created_at: string
  updated_at: string
  message_count?: number
  last_message_preview?: string
}

interface ChatState {
  // Sessions
  sessions: Session[]
  currentSessionId: string | null
  sessionMessages: Record<string, Message[]>  // Cache messages by session ID
  
  // Loading states
  isLoadingSessions: boolean
  isLoadingMessages: boolean
  isSending: boolean
  isGeneratingTitle: boolean
  
  // Streaming
  streamingContent: string
  currentPhase: string | null
  
  // Error handling
  error: string | null
  
  // Actions
  fetchSessions: () => Promise<void>
  createSession: (title?: string) => Promise<Session>
  selectSession: (sessionId: string) => Promise<void>
  deleteSession: (sessionId: string) => Promise<void>
  updateSession: (sessionId: string, data: Partial<Session>) => Promise<void>
  togglePinSession: (sessionId: string) => Promise<void>
  archiveSession: (sessionId: string) => Promise<void>
  generateSessionTitle: (sessionId: string) => Promise<void>
  exportSession: (sessionId: string) => Promise<unknown>
  
  // Messaging
  sendMessage: (content: string) => Promise<void>
  
  // Utilities
  clearError: () => void
  getCurrentSession: () => Session | null
  getSessionMessages: (sessionId: string) => Message[]
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      // Initial state
      sessions: [],
      currentSessionId: null,
      sessionMessages: {},
      isLoadingSessions: false,
      isLoadingMessages: false,
      isSending: false,
      isGeneratingTitle: false,
      streamingContent: '',
      currentPhase: null,
      error: null,

      // Fetch all sessions
      fetchSessions: async () => {
        set({ isLoadingSessions: true, error: null })
        try {
          const response = await api.get('/api/v1/sessions?page_size=100')
          set({ 
            sessions: response.data.sessions,
            isLoadingSessions: false 
          })
        } catch (error: unknown) {
          const message = error instanceof Error ? error.message : 'Failed to load sessions'
          set({ error: message, isLoadingSessions: false })
        }
      },

      // Create new session
      createSession: async (title = 'New Chat') => {
        set({ error: null })
        try {
          const response = await api.post('/api/v1/sessions', { title })
          const session = response.data
          set((state) => ({
            sessions: [session, ...state.sessions],
            currentSessionId: session.id,
            sessionMessages: {
              ...state.sessionMessages,
              [session.id]: []
            }
          }))
          return session
        } catch (error: unknown) {
          const message = error instanceof Error ? error.message : 'Failed to create session'
          set({ error: message })
          throw error
        }
      },

      // Select and load a session
      selectSession: async (sessionId: string) => {
        const { sessionMessages } = get()
        
        // If we have cached messages, use them first
        if (sessionMessages[sessionId]) {
          set({ currentSessionId: sessionId })
        }
        
        set({ isLoadingMessages: true, currentPhase: null, error: null })
        
        try {
          const response = await api.get(`/api/v1/sessions/${sessionId}`)
          const session = response.data
          
          set((state) => ({
            currentSessionId: sessionId,
            sessionMessages: {
              ...state.sessionMessages,
              [sessionId]: session.messages || []
            },
            // Update session in list
            sessions: state.sessions.map(s => 
              s.id === sessionId ? { ...s, ...session } : s
            ),
            isLoadingMessages: false
          }))
        } catch (error: unknown) {
          const message = error instanceof Error ? error.message : 'Failed to load session'
          set({ error: message, isLoadingMessages: false })
        }
      },

      // Delete session
      deleteSession: async (sessionId: string) => {
        try {
          await api.delete(`/api/v1/sessions/${sessionId}`)
          set((state) => {
            const newSessionMessages = { ...state.sessionMessages }
            delete newSessionMessages[sessionId]
            
            return {
              sessions: state.sessions.filter((s) => s.id !== sessionId),
              currentSessionId: state.currentSessionId === sessionId ? null : state.currentSessionId,
              sessionMessages: newSessionMessages
            }
          })
        } catch (error: unknown) {
          const message = error instanceof Error ? error.message : 'Failed to delete session'
          set({ error: message })
        }
      },

      // Update session
      updateSession: async (sessionId: string, data: Partial<Session>) => {
        try {
          const response = await api.patch(`/api/v1/sessions/${sessionId}`, data)
          const updatedSession = response.data
          
          set((state) => ({
            sessions: state.sessions.map((s) =>
              s.id === sessionId ? { ...s, ...updatedSession } : s
            )
          }))
        } catch (error: unknown) {
          const message = error instanceof Error ? error.message : 'Failed to update session'
          set({ error: message })
        }
      },

      // Toggle pin
      togglePinSession: async (sessionId: string) => {
        try {
          const response = await api.post(`/api/v1/sessions/${sessionId}/pin`)
          const updatedSession = response.data
          
          set((state) => ({
            sessions: state.sessions.map((s) =>
              s.id === sessionId ? { ...s, is_pinned: updatedSession.is_pinned } : s
            ).sort((a, b) => {
              // Pinned first, then by updated_at
              if (a.is_pinned !== b.is_pinned) return a.is_pinned ? -1 : 1
              return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
            })
          }))
        } catch (error: unknown) {
          const message = error instanceof Error ? error.message : 'Failed to pin session'
          set({ error: message })
        }
      },

      // Archive session
      archiveSession: async (sessionId: string) => {
        try {
          await api.post(`/api/v1/sessions/${sessionId}/archive`)
          set((state) => ({
            sessions: state.sessions.filter((s) => s.id !== sessionId),
            currentSessionId: state.currentSessionId === sessionId ? null : state.currentSessionId
          }))
        } catch (error: unknown) {
          const message = error instanceof Error ? error.message : 'Failed to archive session'
          set({ error: message })
        }
      },

      // Generate title
      generateSessionTitle: async (sessionId: string) => {
        set({ isGeneratingTitle: true })
        try {
          const response = await api.post(`/api/v1/sessions/${sessionId}/generate-title`)
          const { title, description } = response.data
          
          set((state) => ({
            sessions: state.sessions.map((s) =>
              s.id === sessionId ? { ...s, title, description } : s
            ),
            isGeneratingTitle: false
          }))
        } catch (error: unknown) {
          set({ isGeneratingTitle: false })
        }
      },

      // Export session
      exportSession: async (sessionId: string) => {
        try {
          const response = await api.get(`/api/v1/sessions/${sessionId}/export`)
          return response.data
        } catch (error: unknown) {
          const message = error instanceof Error ? error.message : 'Failed to export session'
          set({ error: message })
          throw error
        }
      },

      // Send message with streaming
      sendMessage: async (content: string) => {
        const { currentSessionId, createSession, generateSessionTitle } = get()
        
        let sessionId = currentSessionId
        
        // Create session if needed
        if (!sessionId) {
          try {
            const session = await createSession()
            sessionId = session.id
          } catch {
            return
          }
        }

        // Add user message immediately
        const userMessage: Message = {
          id: `temp-${Date.now()}`,
          role: 'user',
          content,
          created_at: new Date().toISOString(),
        }

        // Add placeholder for assistant message
        const assistantMessage: Message = {
          id: `temp-assistant-${Date.now()}`,
          role: 'assistant',
          content: '',
          created_at: new Date().toISOString(),
          isStreaming: true,
        }

        set((state) => ({
          sessionMessages: {
            ...state.sessionMessages,
            [sessionId!]: [...(state.sessionMessages[sessionId!] || []), userMessage, assistantMessage]
          },
          isSending: true,
          streamingContent: '',
          currentPhase: 'thinking',
          error: null
        }))

        try {
          const authStorage = localStorage.getItem('auth-storage')
          const token = authStorage ? JSON.parse(authStorage).state.accessToken : ''
          
          const response = await fetch('/api/v1/chat/stream', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              session_id: sessionId,
              message: content,
            }),
          })

          if (!response.ok) {
            throw new Error('Stream request failed')
          }

          const reader = response.body?.getReader()
          if (!reader) throw new Error('No reader available')

          const decoder = new TextDecoder()
          let streamedContent = ''
          let finalMessageId = ''

          while (true) {
            const { done, value } = await reader.read()
            if (done) break

            const chunk = decoder.decode(value)
            const lines = chunk.split('\n')

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6))
                  
                  if (data.event === 'message') {
                    streamedContent += data.data.chunk
                    set((state) => {
                      const messages = [...(state.sessionMessages[sessionId!] || [])]
                      const lastMessage = messages[messages.length - 1]
                      if (lastMessage?.isStreaming) {
                        lastMessage.content = streamedContent
                      }
                      return { 
                        sessionMessages: {
                          ...state.sessionMessages,
                          [sessionId!]: messages
                        },
                        streamingContent: streamedContent 
                      }
                    })
                  } else if (data.event === 'phase') {
                    set({ currentPhase: data.data.phase })
                  } else if (data.event === 'done') {
                    finalMessageId = data.data.assistant_message_id
                  } else if (data.event === 'error') {
                    set({ error: data.data.message })
                  }
                } catch {
                  // Ignore parsing errors for incomplete chunks
                }
              }
            }
          }

          // Finalize the message
          set((state) => {
            const messages = [...(state.sessionMessages[sessionId!] || [])]
            const lastMessage = messages[messages.length - 1]
            if (lastMessage?.isStreaming) {
              lastMessage.isStreaming = false
              if (finalMessageId) {
                lastMessage.id = finalMessageId
              }
            }
            return { 
              sessionMessages: {
                ...state.sessionMessages,
                [sessionId!]: messages
              },
              isSending: false,
              currentPhase: null
            }
          })
          
          // Auto-generate title for new sessions
          const currentMessages = get().sessionMessages[sessionId!] || []
          if (currentMessages.length <= 2) {
            // First message pair - generate title
            setTimeout(() => generateSessionTitle(sessionId!), 500)
          }
          
          // Refresh sessions to update timestamps
          get().fetchSessions()
          
        } catch (error: unknown) {
          const message = error instanceof Error ? error.message : 'Failed to send message'
          set((state) => {
            // Remove temporary messages on error
            const messages = (state.sessionMessages[sessionId!] || []).filter(
              (m) => !m.id.startsWith('temp-')
            )
            return {
              sessionMessages: {
                ...state.sessionMessages,
                [sessionId!]: messages
              },
              error: message,
              isSending: false,
              currentPhase: null,
            }
          })
        }
      },

      // Clear error
      clearError: () => set({ error: null }),
      
      // Get current session
      getCurrentSession: () => {
        const { sessions, currentSessionId } = get()
        return sessions.find(s => s.id === currentSessionId) || null
      },
      
      // Get messages for a session
      getSessionMessages: (sessionId: string) => {
        return get().sessionMessages[sessionId] || []
      }
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({
        currentSessionId: state.currentSessionId,
        // Don't persist messages - fetch fresh from server
      }),
    }
  )
)
