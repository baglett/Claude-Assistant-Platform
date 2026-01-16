# Frontend Feature Roadmap

This document outlines features that can be implemented based on the existing codebase capabilities. Features are organized by priority and complexity.

---

## Current State Analysis

### Existing Frontend
- Basic chat interface (ChatContainer, ChatInput, ChatMessage)
- Zustand state management with localStorage persistence
- DaisyUI component library with Tailwind CSS
- Resume dashboard with profile, skills, job listings, and resume history
- Todo dashboard with CRUD, filtering, and statistics

### Existing Backend Capabilities (Untapped by Frontend)
- **Agent Execution Logs** (`agents.executions`) - Thinking, tool calls, responses
- **Conversation History** (PostgreSQL) - Multiple conversations per user
- **Router Analytics** - Routing decisions, confidence scores
- **Health Checks** (`/health`) - Service status monitoring

---

## Completed Features

### Resume Dashboard
**Status:** Completed | **Route:** `/resume/*`

Full-featured resume management system:
- **Dashboard** (`/resume`) - Overview with stats, profile summary, quick actions
- **Profile** (`/resume/profile`) - Personal info, contact details, professional links
- **Skills** (`/resume/skills`) - CRUD with category/proficiency filtering, featured skills
- **Experience** (`/resume/experience`) - Work history with achievements and skills used
- **Jobs** (`/resume/jobs`) - Job listing scraper with favorite toggle and status tracking
- **History** (`/resume/history`) - Generated resume gallery with match scores

**Components:** ProfileForm, SkillList, ExperienceList, JobListingCard, ResumeCard
**Stores:** profileStore, resumeStore
**API Client:** `Frontend/src/lib/api/resume.ts`

### Todo Dashboard
**Status:** Completed | **Route:** `/todos`

Task management with filtering and statistics:
- Full CRUD operations
- Status and priority filtering
- Todo statistics display
- Cancel and execute actions

---

## Phase 1: Core UI Enhancements (Quick Wins)

### 1.1 Markdown Message Rendering
**Complexity:** Low | **Impact:** High

Render assistant responses with proper markdown formatting.

**Implementation:**
- Install `react-markdown` and `remark-gfm`
- Create `MarkdownContent` component
- Support code blocks with syntax highlighting (`rehype-highlight`)
- Support tables, lists, links

**Files to Create/Modify:**
- `Frontend/src/components/MarkdownContent.tsx` (new)
- `Frontend/src/components/ChatMessage.tsx` (modify)
- `Frontend/package.json` (add dependencies)

---

### 1.2 Message Actions (Copy, Retry)
**Complexity:** Low | **Impact:** Medium

Add action buttons to messages for copy-to-clipboard and retry.

**Implementation:**
- Add hover state with action buttons
- Copy button copies message content
- Retry button resends user message
- Visual feedback (toast notifications)

**Files to Create/Modify:**
- `Frontend/src/components/ChatMessage.tsx` (modify)
- `Frontend/src/components/Toast.tsx` (new)
- `Frontend/src/stores/chatStore.ts` (add retryMessage action)

---

### 1.3 Dark Mode Toggle
**Complexity:** Low | **Impact:** Medium

Add theme switching using DaisyUI's built-in theme support.

**Implementation:**
- Create theme store with Zustand
- Toggle between `light` and `dark` DaisyUI themes
- Persist preference to localStorage
- Add toggle button in header

**Files to Create/Modify:**
- `Frontend/src/stores/themeStore.ts` (new)
- `Frontend/src/app/layout.tsx` (add theme provider)
- `Frontend/src/components/ChatContainer.tsx` (add toggle)

---

### 1.4 Typing Indicator
**Complexity:** Low | **Impact:** Medium

Show animated typing indicator while waiting for response.

**Implementation:**
- Create animated dots component
- Display when `isLoading` is true
- Replace current streaming placeholder

**Files to Create/Modify:**
- `Frontend/src/components/TypingIndicator.tsx` (new)
- `Frontend/src/components/ChatContainer.tsx` (modify)

---

## Phase 2: Todo Dashboard (Medium Complexity)

### 2.1 Todo List Page
**Complexity:** Medium | **Impact:** High

Full todo management interface leveraging existing `/api/todos` endpoints.

**Implementation:**
- Create `/todos` route with App Router
- List todos with filtering (status, priority, agent)
- Create new todos with form
- Edit/delete todos inline
- Status transition buttons

**API Endpoints (Already Exist):**
- `GET /api/todos` - List with filters
- `POST /api/todos` - Create
- `PUT /api/todos/{id}` - Update
- `DELETE /api/todos/{id}` - Delete

**Files to Create:**
- `Frontend/src/app/todos/page.tsx`
- `Frontend/src/app/todos/layout.tsx`
- `Frontend/src/components/todos/TodoList.tsx`
- `Frontend/src/components/todos/TodoItem.tsx`
- `Frontend/src/components/todos/TodoForm.tsx`
- `Frontend/src/components/todos/TodoFilters.tsx`
- `Frontend/src/stores/todoStore.ts`
- `Frontend/src/lib/api/todos.ts`

---

### 2.2 Todo Statistics Dashboard
**Complexity:** Medium | **Impact:** Medium

Visual dashboard showing todo completion rates and agent activity.

**Implementation:**
- Stats cards (total, completed, in progress)
- Completion rate chart (optional: recharts library)
- Todos by agent breakdown
- Recent activity timeline

**Files to Create:**
- `Frontend/src/app/dashboard/page.tsx`
- `Frontend/src/components/dashboard/StatsCards.tsx`
- `Frontend/src/components/dashboard/TodosByAgent.tsx`
- `Frontend/src/components/dashboard/RecentActivity.tsx`

---

## Phase 3: Conversation Management (Medium Complexity)

### 3.1 Conversation History Sidebar
**Complexity:** Medium | **Impact:** High

Browse and switch between past conversations.

**Implementation:**
- Collapsible sidebar with conversation list
- Show first message as conversation title
- Load conversation history on selection
- New conversation button

**Backend Enhancement Needed:**
- `GET /api/chats` - List conversations
- `GET /api/chats/{id}/messages` - Get messages for conversation

**Files to Create:**
- `Frontend/src/components/ConversationSidebar.tsx`
- `Frontend/src/stores/conversationStore.ts`
- `Frontend/src/lib/api/conversations.ts`
- `Backend/src/api/routes/chats.py` (enhance)

---

### 3.2 Search Messages
**Complexity:** Medium | **Impact:** Medium

Full-text search across conversation history.

**Implementation:**
- Search input with debounced query
- Highlight matching text in results
- Click result to navigate to conversation

**Backend Enhancement Needed:**
- `GET /api/chats/search?q=` - Search endpoint

**Files to Create:**
- `Frontend/src/components/SearchDialog.tsx`
- Modify `Backend/src/api/routes/chats.py`

---

## Phase 4: Agent Transparency (Advanced)

### 4.1 Agent Execution Viewer
**Complexity:** High | **Impact:** High

Show what the orchestrator and agents are doing behind the scenes.

**Implementation:**
- Expandable section under assistant messages
- Show which agent handled the request
- Display tool calls made
- Show thinking process (if captured)
- Token usage display

**Backend Enhancement Needed:**
- Link execution_id to chat messages
- `GET /api/executions/{id}` - Get execution details

**Files to Create:**
- `Frontend/src/components/ExecutionDetails.tsx`
- `Frontend/src/components/ToolCallDisplay.tsx`
- `Frontend/src/lib/api/executions.ts`

---

### 4.2 Real-time Streaming Responses
**Complexity:** High | **Impact:** High

Stream responses as they're generated instead of waiting for completion.

**Implementation:**
- Use Server-Sent Events (SSE) or WebSocket
- Stream response chunks to frontend
- Progressive markdown rendering
- Show tool calls in real-time

**Backend Enhancement Needed:**
- `POST /api/chat/stream` - SSE endpoint
- Modify orchestrator to yield chunks

**Files to Create:**
- `Frontend/src/lib/api/stream.ts`
- Modify `Frontend/src/stores/chatStore.ts`
- `Backend/src/api/routes/chat_stream.py` (new)

---

## Phase 5: Multi-Modal & Advanced Features

### 5.1 File Upload Support
**Complexity:** High | **Impact:** Medium

Upload files to include in context (images, documents).

**Implementation:**
- Drag-and-drop zone on chat input
- File preview before sending
- Backend file handling and storage
- Claude vision API for images

**Files to Create:**
- `Frontend/src/components/FileUpload.tsx`
- `Frontend/src/components/FilePreview.tsx`
- `Backend/src/api/routes/files.py`
- `Backend/src/services/file_service.py`

---

### 5.2 Voice Input
**Complexity:** High | **Impact:** Medium

Voice-to-text input using Web Speech API.

**Implementation:**
- Microphone button in chat input
- Real-time transcription display
- Send transcribed text as message

**Files to Create:**
- `Frontend/src/components/VoiceInput.tsx`
- `Frontend/src/hooks/useSpeechRecognition.ts`

---

### 5.3 Keyboard Shortcuts
**Complexity:** Low | **Impact:** Low

Power user keyboard shortcuts.

**Implementation:**
- `Cmd/Ctrl + K` - New conversation
- `Cmd/Ctrl + /` - Focus chat input
- `Cmd/Ctrl + D` - Toggle dark mode
- `Esc` - Clear input

**Files to Create:**
- `Frontend/src/hooks/useKeyboardShortcuts.ts`
- Modify `Frontend/src/app/layout.tsx`

---

## Implementation Priority Matrix

| Feature | Effort | Impact | Priority |
|---------|--------|--------|----------|
| Markdown Rendering | Low | High | **P0** |
| Typing Indicator | Low | Medium | **P0** |
| Dark Mode | Low | Medium | **P1** |
| Message Actions | Low | Medium | **P1** |
| Todo List Page | Medium | High | **P1** |
| Conversation Sidebar | Medium | High | **P2** |
| Agent Execution Viewer | High | High | **P2** |
| Streaming Responses | High | High | **P3** |
| File Upload | High | Medium | **P3** |

---

## Quick Start: Phase 1 Implementation Order

1. **Markdown Rendering** - Immediate visual improvement
2. **Typing Indicator** - Better loading UX
3. **Dark Mode** - User preference
4. **Message Actions** - Productivity feature

Estimated scope: 4-6 component files, 1 new store, 3 package additions.

---

## Tech Stack Additions (When Needed)

| Feature | Package | Purpose |
|---------|---------|---------|
| Markdown | `react-markdown`, `remark-gfm` | Render markdown |
| Syntax Highlighting | `rehype-highlight` | Code block styling |
| Charts | `recharts` | Dashboard visualizations |
| Icons | `lucide-react` | Consistent iconography |
| Date Formatting | `date-fns` | Timestamp display |
| Animations | `framer-motion` | Smooth transitions |

---

## Architecture Guidelines

### New Page Structure
```
Frontend/src/app/
├── page.tsx              # Chat (existing)
├── todos/
│   ├── page.tsx          # Todo list
│   └── layout.tsx        # Todo layout
├── dashboard/
│   └── page.tsx          # Stats dashboard
└── settings/
    └── page.tsx          # User preferences
```

### Component Organization
```
Frontend/src/components/
├── chat/                 # Chat-specific components
├── todos/                # Todo-specific components
├── dashboard/            # Dashboard components
├── common/               # Shared components (Button, Modal, Toast)
└── layout/               # Navigation, Sidebar, Header
```

### Store Organization
```
Frontend/src/stores/
├── chatStore.ts          # Chat state (existing)
├── todoStore.ts          # Todo state
├── themeStore.ts         # Theme preferences
└── uiStore.ts            # UI state (modals, sidebars)
```
