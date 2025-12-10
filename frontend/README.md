# Math Problem Generator - Frontend

A React + TypeScript web interface for the Math Problem Generator backend (Phase 1-5).

## Features

### Authentication (Phase 10)
- **Register Account**: Create account with email, password, and role selection
- **Login System**: Sign in with credentials and receive JWT token
- **Role Management**: Student, Teacher, and Admin roles with different access levels
- **Automatic Token Management**: Token persisted and automatically restored from localStorage
- **Teacher Dashboard**: Protected dashboard accessible only to teachers and admins
- **Logout**: Secure logout that clears authentication state

### Student Interface
- **Topic & Difficulty Selection**: Browse available topics and select difficulty level
- **Smart Recommendations**: Get difficulty recommendations based on past performance
- **Problem Generation**: Generate problems with LaTeX rendering
- **Answer Submission**: Submit answers and get instant feedback
- **Hint System**: Request hints powered by LLM (Dummy or OpenAI)
- **Solution Display**: View full solutions after attempting problems
- **Anonymous Access**: Use app without creating an account (legacy support)

### Teacher Interface
- **Access Control**: Secure teacher dashboard accessible to authenticated teachers
- **Student Analytics**: View performance metrics per student and topic
- **Difficulty Recommendations**: See AI-powered recommendations for each student
- **Performance Tracking**: Monitor success rates, attempt counts, and time metrics

## Tech Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **HTTP Client**: Axios
- **Styling**: Plain CSS (easily extensible with Tailwind/CSS Modules)
- **State Management**: React hooks (lightweight, no Redux needed for Phase 6)

## Setup & Development

### Prerequisites

- Node.js 16+ and npm 8+

### Installation

```bash
cd frontend
npm install
```

### Environment Configuration

Copy and configure `.env.local`:

```bash
cp .env.example .env.local
```

Edit `.env.local`:

```env
# Backend API URL (ensure FastAPI server is running on this port)
VITE_API_BASE_URL=http://localhost:8000

# Teacher access code (for legacy access code mode)
VITE_TEACHER_ACCESS_CODE=TEACHER123

# Optional: API key for server-to-server authentication
VITE_TEACHER_API_KEY=your-api-key-here
```

### Authentication Setup (Phase 10)

1. **No Setup Required**: Authentication is built-in and backward compatible
2. **Register Page**: Navigate to `/register` to create an account
3. **Login Page**: Navigate to `/login` to sign in
4. **Anonymous Access**: Users can still access student features without logging in
5. **JWT Token**: Token automatically stored and restored from localStorage

**Important**: In production, ensure your backend is served over HTTPS to securely transmit tokens.

### Running the Development Server

```bash
npm run dev
```

Server will run at `http://localhost:5173`

The Vite dev server includes automatic proxying to the backend API.

### Building for Production

```bash
npm run build
```

Output will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── services/
│   │   ├── http_client.ts    # API client wrapper with auth token management
│   │   └── __tests__/
│   │       └── http_client_auth.test.ts
│   ├── types/
│   │   └── api_types.ts      # TypeScript interfaces including auth types
│   ├── components/
│   │   ├── Header.tsx        # Top navigation & auth UI
│   │   ├── Header.css
│   │   ├── TopicSelector.tsx # Topic selection cards
│   │   ├── TopicSelector.css
│   │   ├── DifficultySelector.tsx
│   │   ├── ProblemView.tsx   # Main problem display & interaction
│   │   ├── ProblemView.css
│   │   ├── MathText.tsx      # LaTeX rendering component
│   │   └── MathText.css
│   ├── hooks/
│   │   ├── useUserIdentity.ts  # Legacy user ID & role management
│   │   ├── useAuthUser.ts      # New auth state management hook
│   │   └── __tests__/
│   │       └── useAuthUser.test.tsx
│   ├── pages/
│   │   ├── LoginPage.tsx     # Login form (new)
│   │   ├── LoginPage.css
│   │   ├── RegisterPage.tsx  # Registration form (new)
│   │   ├── RegisterPage.css
│   │   ├── StudentDashboard.tsx
│   │   ├── StudentDashboard.css
│   │   ├── TeacherDashboard.tsx
│   │   ├── TeacherDashboard.css
│   │   └── __tests__/
│   │       ├── LoginPage.test.tsx
│   │       └── RegisterPage.test.tsx
│   ├── api/
│   │   ├── client.ts         # Legacy API client
│   │   └── types.ts          # Legacy TypeScript interfaces
│   ├── config.ts             # Environment-based configuration
│   ├── App.tsx               # Main app component
│   ├── App.css               # Global styles
│   └── main.tsx              # React DOM entry point
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
└── .env.local                # Local environment variables
```

## API Integration

The frontend connects to the FastAPI backend via HTTP JSON. All endpoints are defined in `src/services/http_client.ts`.

### Authentication Endpoints (Phase 10)
- `POST /auth/register` - Register new user account
- `POST /auth/login` - Authenticate and get JWT token
- `GET /me/stats/{topicId}` - Get authenticated user stats
- `GET /me/recommend/{topicId}` - Get authenticated user difficulty recommendation

### Backend Endpoints Used

- `GET /topics` - Fetch available topics
- `GET /generate?topic_id=...&difficulty=...` - Generate a problem
- `POST /attempt` - Submit an attempt (authenticated or anonymous)
- `GET /user/{userId}/stats/{topicId}` - Get user statistics (anonymous)
- `GET /user/{userId}/recommend/{topicId}` - Get difficulty recommendation (anonymous)
- `POST /hint` - Request a hint
- `GET /health` - Health check

See `src/api/types.ts` for the full interface definitions.

## User Identity & Persistence

### Authentication System (Phase 10)

The frontend now supports full JWT-based authentication with role management:

#### Authentication Flow
1. **Register**: Create account at `/register` with email, password, display name, and role
2. **Login**: Sign in at `/login` with email and password
3. **Token Storage**: JWT token stored in `localStorage` under `mpg_token`
4. **Auto-Login**: Token automatically restored from localStorage on page refresh
5. **Logout**: Clear session and token via logout button in header

#### User Identity Model
- **backendUserId**: From JWT token, identifies authenticated user (null if anonymous)
- **legacyUserId**: UUID generated on first visit, used for anonymous users
- **email**: Stored from user profile during login/register
- **displayName**: Optional user display name
- **role**: "anonymous" | "student" | "teacher" | "admin"
- **authToken**: JWT access token (Bearer token format)

#### localStorage Keys
```javascript
mpg_token          // JWT access token
mpg_user_info      // JSON {user_id, role, email?, display_name?}
mpg_legacy_user_id // UUID for anonymous users
```

#### Role-Based Access
- **Anonymous**: Can access student features with legacy UUID
- **Student**: Registered student account, tracked with backend user_id
- **Teacher**: Unlock teacher dashboard, view student analytics, create assignments
- **Admin**: Full system access (teacher features + admin tools)

#### Protected Components
- `/login` - Login page (accessible to all)
- `/register` - Registration page (accessible to all)
- `/teacher` - TeacherDashboard (shows "auth required" if not teacher or admin)
- Header shows appropriate UI based on authentication state

### Legacy Anonymous Mode (Backward Compatible)
- **User ID**: Automatically generated UUID, stored in localStorage as `mpg_legacy_user_id`
- **Role**: `anonymous`
- Anonymous users still fully supported - no authentication required
- When user logs in, backend user_id takes priority; legacy UUID used as fallback

### Student Mode (Legacy)
- **User ID**: Automatically generated UUID, stored in localStorage
- **Role**: `student`
- No authentication required (backward compatible)

## LaTeX Rendering

Currently, LaTeX is rendered as plain text in `<code>` blocks. To enable full LaTeX rendering:

### Option 1: KaTeX (Recommended for lightweight)

```bash
npm install katex react-katex
```

Update `src/components/MathText.tsx`:

```typescript
import KaTeX from 'react-katex';
import 'katex/dist/katex.min.css';

export function MathText({ latex, inline = false }: MathTextProps) {
  return (
    <KaTeX
      math={latex}
      block={!inline}
      errorColor="#cc0000"
    />
  );
}
```

### Option 2: MathJax

```bash
npm install mathjax-full
```

(More complex setup - see MathJax documentation)

## State Management

The frontend uses React hooks for state management:

- **useUserIdentity**: User ID and role (localStorage-persisted)
- **useState**: Local component state
- **useEffect**: Side effects (API calls, etc.)

For Phase 6, this lightweight approach is sufficient. If complexity grows, consider adding:
- Redux or Zustand for global state
- React Query for server state management

## Styling Approach

The project uses **plain CSS** with a global design system defined in `App.css`. CSS files are co-located with components for easy maintenance.

### Design Tokens (from `App.css`)

```css
--primary: #667eea
--secondary: #764ba2
--success: #22c55e
--warning: #f59e0b
--error: #ef4444
```

To add Tailwind CSS:

```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

## Error Handling

- **Network Errors**: Displayed as error banners in components
- **API Errors**: Caught and displayed to users
- **Loading States**: Components show "Loading..." feedback
- **User Feedback**: Clear success/error messages for all actions

## Testing

To add unit tests with Vitest:

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom
```

Example test structure:

```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Header } from '../components/Header';

describe('Header', () => {
  it('displays user role', () => {
    render(
      <Header
        role="student"
        isTeacher={false}
        userId="abc123"
        onSwitchToTeacher={() => false}
        onSwitchToStudent={() => {}}
      />
    );
    expect(screen.getByText(/role: student/i)).toBeInTheDocument();
  });
});
```

## Accessibility

The frontend follows basic accessibility patterns:

- Semantic HTML elements
- ARIA labels where needed (in `Header` modal)
- Keyboard support (Enter key submits forms)
- Color contrast meets WCAG AA standards
- Focus management for modals

## Typical User Flows

### Anonymous Student
1. Visit app → automatically assigned UUID
2. Select topic and difficulty
3. Generate and solve problems
4. Stats tracked with UUID (legacy mode)

### New User Registration
1. Click "Register" in header
2. Enter email, password, display name, select role (student/teacher)
3. Submit form → account created, logged in automatically
4. Redirected to home page with authenticated UI

### Returning User
1. Click "Login" in header
2. Enter email and password
3. Submit → JWT token issued and stored
4. Redirected to home page with authenticated UI
5. On next visit, token restored from localStorage → auto-logged in

### Teacher Onboarding
1. Register with teacher role
2. After login, navigate to `/teacher` or TeacherDashboard
3. View student statistics and performance analytics
4. Create assignments for students

### Student Using Authenticated App
1. Login with email/password
2. All problem solving tracked with backend user_id
3. Stats available at `/me/stats/{topicId}`
4. Recommendations from `/me/recommend/{topicId}`
5. Logout clears session and token

## Browser Support

- Chrome/Edge 88+
- Firefox 87+
- Safari 14+
- Mobile browsers (responsive design)

## Performance Optimizations

- Code splitting via Vite
- Tree-shaking of unused code
- CSS is co-located (easy to remove unused styles)
- Lazy loading of images/fonts (future)
- React.StrictMode for development warnings

## Troubleshooting

### "Cannot find module 'react'"

Ensure you've run `npm install`. If using Node 16, use `npm install --legacy-peer-deps`.

### API calls fail with CORS errors

- Ensure FastAPI backend is running on the configured `VITE_API_BASE_URL`
- Check that backend has CORS enabled (it should, from Phase 1-5)
- Verify `.env.local` has the correct backend URL

### Login fails with 401 Unauthorized

- Verify you're using correct email and password
- Check that backend `/auth/login` endpoint is accessible
- Ensure backend is running (check `VITE_API_BASE_URL`)
- Check browser console for detailed error message

### Registration fails

- Verify email format is valid
- Ensure password is at least 6 characters
- Check that email isn't already registered
- Verify backend `/auth/register` endpoint is accessible

### Token is not persisting across page reloads

- Check browser localStorage (`mpg_token` key should exist)
- Verify localStorage is not disabled/cleared by browser
- Check browser private/incognito mode (clears localStorage on close)
- Clear browser cache and try again

### Can't access teacher dashboard

- Login with a teacher or admin account
- If using access code mode, verify access code in config
- Check that `isTeacher` or `isAdmin` is true in user profile
- Review TeacherDashboard for auth guard message

### Lost JWT token after closing browser

- This is expected behavior for security
- Token stored in localStorage should persist across sessions
- If cleared, user needs to login again
- In production, consider using HttpOnly cookies for better security

### Teacher mode won't unlock

- Confirm `.env.local` has `VITE_TEACHER_ACCESS_CODE` set
- Verify you're entering the exact access code (case-sensitive)
- Clear browser localStorage and reload if stuck

### LaTeX not rendering

- Currently renders as plain text in `<code>` blocks
- To enable KaTeX: follow "LaTeX Rendering" section above

## Future Enhancements (Phase 11+)

- [ ] Full LaTeX rendering with KaTeX/MathJax
- [ ] Problem history & detailed analytics
- [ ] Custom problem set creation (teacher)
- [ ] Shareable problem set links
- [ ] Real-time collaboration features
- [ ] Mobile app via React Native
- [ ] Dark mode support
- [ ] Internationalization (i18n)
- [ ] Advanced testing coverage (full E2E test suite)
- [ ] OAuth2 integration (Google, GitHub login)
- [ ] Email verification for registration
- [ ] Password reset functionality
- [ ] User profile customization
- [ ] Student groups and class management
- [ ] Assignment grading interface

## Contributing

1. Follow the existing code style
2. Keep components small and focused
3. Use TypeScript strict mode
4. Add comments for complex logic
5. Test before submitting changes

## License

MIT (same as backend)
