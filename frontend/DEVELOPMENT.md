# Frontend Development Guide

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable React components
│   ├── pages/              # Page-level components
│   ├── services/           # API communication layer
│   ├── utils/              # Utility functions
│   ├── types/              # TypeScript type definitions
│   ├── __tests__/          # Unit tests
│   ├── App.tsx             # Root component
│   └── main.tsx            # Entry point
├── public/                 # Static assets
├── package.json            # Dependencies and scripts
├── vite.config.ts          # Vite configuration
├── tsconfig.json           # TypeScript configuration
└── vitest.config.ts        # Vitest test runner configuration
```

## Installation & Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Run tests
npm run test

# Run tests with coverage
npm run test:coverage
```

## Architecture Overview

### Component Hierarchy
- `App` - Root component with routing
- `Navbar` - Navigation bar
- `Sidebar` - Student/Teacher navigation
- `StudentDashboard` - Main student interface
- `ProblemSolver` - Problem solving interface
- `ProblemAnswer` - Answer submission component
- `ProgressChart` - Progress visualization

### State Management
- Uses React Context API for:
  - Authentication state
  - User profile
  - Current problem state
  - Progress tracking

### API Layer (`services/http_client.ts`)
- Centralized HTTP client with built-in authentication
- Type-safe API endpoints
- Automatic token management
- Error handling

## Development Patterns

### API Communication
```typescript
// Importing API functions
import { authAPI, problemAPI, submissionAPI, progressAPI } from '@/services/http_client';

// Using API calls
const result = await authAPI.login(email, password);
if (result.success) {
  // Handle success
} else {
  // Handle error
}
```

### Component Structure
```typescript
import React, { useState, useEffect } from 'react';
import './ComponentName.css';

interface Props {
  // Define component props
}

const ComponentName: React.FC<Props> = ({ prop1, prop2 }) => {
  const [state, setState] = useState(initial);

  useEffect(() => {
    // Setup effects
  }, []);

  return (
    <div>
      {/* Component JSX */}
    </div>
  );
};

export default ComponentName;
```

### Styling
- CSS files colocated with components
- BEM naming convention for CSS classes
- Responsive design with mobile-first approach
- CSS variables for theming

## Key Components

### StudentDashboard
- Displays student progress statistics
- Shows current problem
- Navigation to problem-solving interface
- Progress tracking and analytics

### ProblemSolver
- Renders math problem
- Handles user input
- Provides feedback on answers
- Tracks attempts and scores

### ProgressChart
- Visualizes student performance
- Shows scores by problem type
- Displays improvement over time
- Responsive chart rendering

## Testing

### Test Files
- Located in `src/__tests__/` directory
- Use Vitest test runner
- Mock data utilities for testing

### Running Tests
```bash
# Run all tests
npm run test

# Run specific test file
npm run test -- validation.test.ts

# Run tests with watch mode
npm run test -- --watch

# Generate coverage report
npm run test:coverage
```

### Test Categories
1. **Unit Tests** - Individual function/component testing
2. **Integration Tests** - API integration testing
3. **Component Tests** - React component behavior testing

## Type Safety

### API Response Types
All API responses use consistent typing:
```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}
```

### Component Props
Always define Props interfaces:
```typescript
interface ComponentProps {
  title: string;
  onSubmit: (value: number) => void;
  disabled?: boolean;
}
```

## CSS Architecture

### Naming Convention
```css
/* Block */
.component-name { }

/* Block - Element */
.component-name__title { }

/* Block - Element - Modifier */
.component-name__button--active { }
```

### Responsive Breakpoints
```css
@media (max-width: 768px) {
  /* Tablet and mobile styles */
}

@media (max-width: 480px) {
  /* Mobile-only styles */
}
```

## Common Tasks

### Adding a New Page
1. Create component in `src/pages/`
2. Define Props interface
3. Create accompanying CSS file
4. Add route in `App.tsx`
5. Update navigation

### Adding a New API Endpoint
1. Define types in `src/types/api_types.ts`
2. Add endpoint function in `src/services/http_client.ts`
3. Import and use in components
4. Test with mock data

### Adding a New Component
1. Create TSX file in `src/components/`
2. Define Props interface
3. Create CSS file with BEM naming
4. Export default component
5. Create unit tests in `src/__tests__/`

## Performance Optimization

### Code Splitting
- Lazy load pages with React.lazy()
- Dynamic imports for large components

### Memoization
```typescript
const MemoizedComponent = React.memo(Component);
const memoizedCallback = useCallback(callback, [dependencies]);
```

### Asset Optimization
- SVG icons for crisp rendering
- Minified CSS and JS in production
- Image optimization for faster loading

## Debugging

### Browser DevTools
- React Developer Tools extension
- Network tab for API debugging
- Console for logging

### Common Issues
1. **CORS errors** - Check API URL configuration
2. **State not updating** - Ensure proper dependency arrays
3. **Memory leaks** - Clean up effects with return functions
4. **Type errors** - Run `npm run type-check`

## Deployment

### Building for Production
```bash
npm run build
# Creates optimized build in dist/
```

### Environment Variables
Create `.env` file:
```
VITE_API_URL=https://api.example.com
VITE_APP_NAME=Math Problem Generator
```

### Deployment Checklist
- [ ] Run tests: `npm run test`
- [ ] Check types: `npm run type-check`
- [ ] Build: `npm run build`
- [ ] Test build locally: `npm run preview`
- [ ] Review bundle size
- [ ] Test on multiple devices

## Best Practices

1. **Component Composition** - Keep components small and focused
2. **Props Validation** - Always define and validate props
3. **Error Handling** - Handle API errors gracefully
4. **Loading States** - Show feedback during data fetching
5. **Accessibility** - Use semantic HTML and ARIA attributes
6. **Code Organization** - Maintain clear file structure
7. **Git Workflow** - Create feature branches for new work
8. **Documentation** - Comment complex logic and document APIs

## Resources

- [React Documentation](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Vite Guide](https://vitejs.dev/)
- [Vitest Documentation](https://vitest.dev/)
- [BEM Methodology](http://getbem.com/)

## Troubleshooting

### Module not found errors
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Port already in use
```bash
# Change dev server port
npm run dev -- --port 3001
```

### Build errors
```bash
# Check TypeScript compilation
npm run type-check

# Check for linting issues
npm run lint
```
