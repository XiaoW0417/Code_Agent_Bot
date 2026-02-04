import { useState, useMemo } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useChatStore, Session } from '../stores/chat'
import { useAuthStore } from '../stores/auth'
import { 
  Plus, 
  MessageSquare, 
  Trash2, 
  LogOut, 
  Pin,
  PinOff,
  Search,
  X,
  MoreHorizontal,
  Archive,
  Download,
  Edit2,
  Zap,
  ChevronDown,
  ChevronRight
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

interface SidebarProps {
  onClose?: () => void
}

export default function Sidebar({ onClose }: SidebarProps) {
  const navigate = useNavigate()
  const { sessionId } = useParams()
  const [searchQuery, setSearchQuery] = useState('')
  const [showPinned, setShowPinned] = useState(true)
  const [showRecent, setShowRecent] = useState(true)
  
  const { 
    sessions, 
    isLoadingSessions, 
    createSession, 
    deleteSession,
    togglePinSession,
    archiveSession,
    exportSession
  } = useChatStore()
  const { user, logout } = useAuthStore()

  // Filter and group sessions
  const { pinnedSessions, recentSessions } = useMemo(() => {
    let filtered = sessions
    
    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = sessions.filter(s => 
        s.title.toLowerCase().includes(query) ||
        s.last_message_preview?.toLowerCase().includes(query)
      )
    }
    
    return {
      pinnedSessions: filtered.filter(s => s.is_pinned),
      recentSessions: filtered.filter(s => !s.is_pinned)
    }
  }, [sessions, searchQuery])

  const handleNewChat = async () => {
    try {
      const session = await createSession()
      navigate(`/chat/${session.id}`)
      onClose?.()
    } catch (error) {
      console.error('Failed to create session:', error)
    }
  }

  const handleSelectSession = (id: string) => {
    navigate(`/chat/${id}`)
    onClose?.()
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const handleExport = async (id: string) => {
    try {
      const data = await exportSession(id)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `chat-export-${id}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to export:', error)
    }
  }

  return (
    <aside className="w-72 h-full bg-bg-secondary border-r border-border-default flex flex-col">
      {/* Logo */}
      <div className="p-4 border-b border-border-default">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center shadow-lg shadow-accent-blue/20">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-display font-bold text-lg gradient-text">Agent Bot</h1>
            <p className="text-xs text-text-secondary">AI Coding Assistant</p>
          </div>
        </div>
      </div>

      {/* New Chat Button */}
      <div className="p-3">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-gradient-to-r from-accent-blue to-accent-purple text-white hover:opacity-90 transition-all duration-200 font-medium shadow-lg shadow-accent-blue/20"
        >
          <Plus size={18} />
          <span>New Chat</span>
        </button>
      </div>

      {/* Search */}
      <div className="px-3 pb-2">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversations..."
            className="w-full pl-9 pr-8 py-2 rounded-lg bg-bg-tertiary border border-border-default focus:border-accent-blue/50 outline-none text-sm transition-colors"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-bg-elevated text-text-tertiary"
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto px-3 py-2">
        {isLoadingSessions ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
          </div>
        ) : sessions.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            {/* Pinned Sessions */}
            {pinnedSessions.length > 0 && (
              <SessionGroup
                title="Pinned"
                icon={<Pin size={12} />}
                sessions={pinnedSessions}
                isOpen={showPinned}
                onToggle={() => setShowPinned(!showPinned)}
                currentSessionId={sessionId}
                onSelect={handleSelectSession}
                onDelete={deleteSession}
                onPin={togglePinSession}
                onArchive={archiveSession}
                onExport={handleExport}
              />
            )}

            {/* Recent Sessions */}
            <SessionGroup
              title="Recent"
              sessions={recentSessions}
              isOpen={showRecent}
              onToggle={() => setShowRecent(!showRecent)}
              currentSessionId={sessionId}
              onSelect={handleSelectSession}
              onDelete={deleteSession}
              onPin={togglePinSession}
              onArchive={archiveSession}
              onExport={handleExport}
            />
          </>
        )}
      </div>

      {/* User Section */}
      <div className="p-3 border-t border-border-default">
        <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-bg-tertiary transition-colors">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-accent-purple to-accent-cyan flex items-center justify-center text-sm font-bold shadow-md">
            {user?.display_name?.[0] || user?.username?.[0] || '?'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.display_name || user?.username}</p>
            <p className="text-xs text-text-secondary truncate">{user?.email}</p>
          </div>
          <button
            onClick={handleLogout}
            className="p-2 rounded-lg hover:bg-accent-red/10 text-text-secondary hover:text-accent-red transition-colors"
            title="Logout"
          >
            <LogOut size={18} />
          </button>
        </div>
      </div>
    </aside>
  )
}

function EmptyState() {
  return (
    <div className="text-center py-8 text-text-secondary">
      <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-bg-tertiary flex items-center justify-center">
        <MessageSquare className="w-8 h-8 opacity-50" />
      </div>
      <p className="text-sm font-medium">No conversations yet</p>
      <p className="text-xs mt-1 text-text-tertiary">Start a new chat to begin</p>
    </div>
  )
}

interface SessionGroupProps {
  title: string
  icon?: React.ReactNode
  sessions: Session[]
  isOpen: boolean
  onToggle: () => void
  currentSessionId?: string
  onSelect: (id: string) => void
  onDelete: (id: string) => void
  onPin: (id: string) => void
  onArchive: (id: string) => void
  onExport: (id: string) => void
}

function SessionGroup({
  title,
  icon,
  sessions,
  isOpen,
  onToggle,
  currentSessionId,
  onSelect,
  onDelete,
  onPin,
  onArchive,
  onExport
}: SessionGroupProps) {
  if (sessions.length === 0) return null
  
  return (
    <div className="mb-4">
      <button
        onClick={onToggle}
        className="flex items-center gap-2 w-full px-2 py-1 text-xs font-medium text-text-tertiary uppercase tracking-wider hover:text-text-secondary transition-colors"
      >
        {isOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        {icon}
        <span>{title}</span>
        <span className="ml-auto text-text-tertiary">{sessions.length}</span>
      </button>
      
      {isOpen && (
        <div className="mt-1 space-y-1">
          {sessions.map((session) => (
            <SessionItem
              key={session.id}
              session={session}
              isActive={session.id === currentSessionId}
              onSelect={() => onSelect(session.id)}
              onDelete={() => onDelete(session.id)}
              onPin={() => onPin(session.id)}
              onArchive={() => onArchive(session.id)}
              onExport={() => onExport(session.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

interface SessionItemProps {
  session: Session
  isActive: boolean
  onSelect: () => void
  onDelete: () => void
  onPin: () => void
  onArchive: () => void
  onExport: () => void
}

function SessionItem({ session, isActive, onSelect, onDelete, onPin, onArchive, onExport }: SessionItemProps) {
  const [showMenu, setShowMenu] = useState(false)

  const handleAction = (action: () => void) => (e: React.MouseEvent) => {
    e.stopPropagation()
    action()
    setShowMenu(false)
  }

  return (
    <div
      onClick={onSelect}
      className={clsx(
        'group relative flex items-start gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-200',
        isActive
          ? 'bg-accent-blue/10 border border-accent-blue/30'
          : 'hover:bg-bg-tertiary border border-transparent'
      )}
    >
      {/* Icon */}
      <div className="flex-shrink-0 mt-0.5">
        {session.is_pinned ? (
          <Pin size={14} className="text-accent-yellow" />
        ) : (
          <MessageSquare
            size={14}
            className={clsx(isActive ? 'text-accent-blue' : 'text-text-secondary')}
          />
        )}
      </div>
      
      {/* Content */}
      <div className="flex-1 min-w-0">
        <p
          className={clsx(
            'text-sm truncate',
            isActive ? 'text-accent-blue font-medium' : 'text-text-primary'
          )}
        >
          {session.title}
        </p>
        {session.last_message_preview && (
          <p className="text-xs text-text-tertiary truncate mt-0.5">
            {session.last_message_preview}
          </p>
        )}
        <p className="text-xs text-text-tertiary mt-1">
          {formatDistanceToNow(new Date(session.updated_at), { addSuffix: true })}
        </p>
      </div>
      
      {/* Actions Menu */}
      <div className="relative">
        <button
          onClick={(e) => {
            e.stopPropagation()
            setShowMenu(!showMenu)
          }}
          className={clsx(
            'p-1 rounded transition-all',
            showMenu ? 'bg-bg-elevated' : 'opacity-0 group-hover:opacity-100 hover:bg-bg-elevated'
          )}
        >
          <MoreHorizontal size={14} className="text-text-secondary" />
        </button>
        
        {showMenu && (
          <>
            <div 
              className="fixed inset-0 z-10" 
              onClick={(e) => {
                e.stopPropagation()
                setShowMenu(false)
              }} 
            />
            <div className="absolute right-0 top-full mt-1 w-36 py-1 bg-bg-elevated border border-border-default rounded-lg shadow-xl z-20 animate-fade-in">
              <MenuItem
                icon={session.is_pinned ? <PinOff size={14} /> : <Pin size={14} />}
                label={session.is_pinned ? 'Unpin' : 'Pin'}
                onClick={handleAction(onPin)}
              />
              <MenuItem
                icon={<Download size={14} />}
                label="Export"
                onClick={handleAction(onExport)}
              />
              <MenuItem
                icon={<Archive size={14} />}
                label="Archive"
                onClick={handleAction(onArchive)}
              />
              <div className="my-1 border-t border-border-default" />
              <MenuItem
                icon={<Trash2 size={14} />}
                label="Delete"
                onClick={handleAction(onDelete)}
                danger
              />
            </div>
          </>
        )}
      </div>
    </div>
  )
}

interface MenuItemProps {
  icon: React.ReactNode
  label: string
  onClick: (e: React.MouseEvent) => void
  danger?: boolean
}

function MenuItem({ icon, label, onClick, danger }: MenuItemProps) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'w-full flex items-center gap-2 px-3 py-1.5 text-sm transition-colors',
        danger
          ? 'text-accent-red hover:bg-accent-red/10'
          : 'text-text-primary hover:bg-bg-tertiary'
      )}
    >
      {icon}
      <span>{label}</span>
    </button>
  )
}
