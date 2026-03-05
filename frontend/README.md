# Frontend - AI Assistant Web App

Next.js frontend สำหรับ Internal AI Assistant

## Tech Stack

- **Next.js 14** - React framework (App Router)
- **TypeScript** - Type safety
- **TailwindCSS** - Styling
- **shadcn/ui** - UI components (to be added)
- **Supabase Auth** - Authentication

## Setup

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env.local
# Edit .env.local with your credentials

# Run development server
npm run dev
```

## Project Structure

```
frontend/
├── src/
│   ├── app/                # Next.js App Router
│   │   ├── (auth)/         # Auth routes
│   │   ├── (dashboard)/    # Protected routes
│   │   └── api/            # API routes (proxy)
│   ├── components/         # React components
│   ├── hooks/              # Custom hooks
│   ├── lib/                # Utilities
│   └── types/              # TypeScript types
├── public/                 # Static assets
└── package.json
```

## Development

```bash
# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## Deployment

Deploy to GCP Cloud Run using GitHub Actions workflow.
