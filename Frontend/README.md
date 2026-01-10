# Claude Assistant Platform - Frontend

Next.js frontend providing a chat interface for the Claude orchestrator agent.

## Tech Stack

- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS + DaisyUI
- **State Management**: Zustand

## Quick Start

### Local Development

```powershell
# Navigate to frontend directory
cd Frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### With Docker

```powershell
# From project root
docker-compose up frontend backend db
```

## Project Structure

```
Frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx      # Root layout with theme
│   │   ├── page.tsx        # Main chat page
│   │   └── globals.css     # Global styles
│   ├── components/
│   │   ├── ChatContainer.tsx   # Main chat container
│   │   ├── ChatMessage.tsx     # Individual message
│   │   └── ChatInput.tsx       # Message input
│   └── stores/
│       └── chatStore.ts    # Zustand chat state
├── package.json
├── tailwind.config.ts
├── next.config.ts
├── tsconfig.json
└── Dockerfile
```

## Features

- Real-time chat with Claude orchestrator
- Message history persistence (localStorage)
- Typing indicators while waiting for response
- Code block formatting in responses
- Responsive design
- Dark theme (Claude-branded)
- Clear conversation functionality

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API URL |

## Development

```powershell
# Run development server with hot reload
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Lint code
npm run lint
```

## Themes

The app uses a custom "claude" theme by default. Available themes:
- `claude` (default dark theme)
- `light`
- `dark`
- `cyberpunk`
- `synthwave`

Change theme in `src/app/layout.tsx`:
```tsx
<html lang="en" data-theme="claude">
```
