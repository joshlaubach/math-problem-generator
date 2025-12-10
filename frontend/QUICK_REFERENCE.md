# Frontend Quick Reference Guide

## 🚀 Getting Started (2 minutes)

```bash
cd frontend
npm install
npm run dev
# Opens http://localhost:5173
```

## 📁 Key Files You'll Use

### Services (API Communication)
- **`src/services/http_client.ts`** - All API calls go here
  ```typescript
  import { authAPI, problemAPI, submissionAPI, progressAPI } from '@/services/http_client';
  
  // Login
  const result = await authAPI.login(email, password);
  
  // Get next problem
  const problemResult = await problemAPI.getNextProblem();
  
  // Submit answer
  const submission = await submissionAPI.submitAnswer(problemId, 42);
  ```

### Types (TypeScript Definitions)
- **`src/types/api_types.ts`** - All API response types
  ```typescript
  import type { ApiResponse, ProblemResponse, SubmissionResponse } from '@/types/api_types';
  ```

### Utilities (Helpers)
- **`src/utils/test_validation.ts`** - Answer validation
  ```typescript
  import { isAnswerCorrect, parseAnswerInput } from '@/utils/test_validation';
  
  const answer = parseAnswerInput(userInput); // "42" → 42
  const correct = isAnswerCorrect(expected, answer); // true/false
  ```

- **`src/utils/mock_data.ts`** - Test data
  ```typescript
  import { getMockProblem, mockStudent, getRandomMockProblem } from '@/utils/mock_data';
  ```

## 🎨 Styling Patterns

```css
/* Block */
.component-name { }

/* Element */
.component-name__title { }

/* Modifier */
.component-name__button--active { }

/* Mobile first */
@media (max-width: 768px) {
  /* tablet/mobile styles */
}
```

## 🧪 Testing Quick Commands

```bash
# Run all tests
npm run test

# Run specific test file
npm run test -- validation.test.ts

# Watch mode
npm run test -- --watch

# Coverage report
npm run test:coverage
```

## 📝 Common Tasks

### Making an API Call
```typescript
const result = await problemAPI.getNextProblem();
if (result.success) {
  // Handle success
  console.log(result.data);
} else {
  // Handle error
  console.error(result.error);
}
```

### Validating User Input
```typescript
const input = userInput.trim();
if (!isValidNumberInput(input)) {
  setError("Please enter a valid number");
  return;
}

const answer = parseAnswerInput(input)!;
const isCorrect = isAnswerCorrect(expectedAnswer, answer);
```

### Creating a New Component
```typescript
import React from 'react';
import './MyComponent.css';

interface MyComponentProps {
  title: string;
  onAction: () => void;
}

const MyComponent: React.FC<MyComponentProps> = ({ title, onAction }) => {
  return (
    <div className="my-component">
      <h2 className="my-component__title">{title}</h2>
      <button className="my-component__button" onClick={onAction}>
        Click me
      </button>
    </div>
  );
};

export default MyComponent;
```

### Adding a Test
```typescript
import { describe, it, expect } from 'vitest';
import { myFunction } from '@/utils/myUtil';

describe('myFunction', () => {
  it('should do something', () => {
    const result = myFunction(input);
    expect(result).toBe(expected);
  });
});
```

## 🔧 Project Structure

```
src/
├── components/          # Reusable components
├── pages/              # Page-level components
├── services/           # API communication (HTTP client)
├── types/              # TypeScript definitions
├── utils/              # Helper functions
├── __tests__/          # Unit tests
├── App.tsx             # Root component
└── main.tsx            # Entry point
```

## 🐛 Debugging Tips

### Check API Responses
```typescript
// In browser console
const response = await fetch('http://localhost:8000/api/problems/next');
const data = await response.json();
console.log(data);
```

### Check Type Definitions
```bash
npm run type-check
```

### Check Bundle Size
```bash
npm run build
# Check dist/ size
```

### Common Issues
| Issue | Solution |
|-------|----------|
| "Cannot find module" | Run `npm install` |
| TypeScript errors | Run `npm run type-check` |
| Tests failing | Run `npm run test -- --watch` |
| Port in use | `npm run dev -- --port 3001` |

## 📚 Documentation

- **Full Guide**: See `frontend/DEVELOPMENT.md`
- **Architecture**: See `README.md`
- **Phase 7 Details**: See `PHASE7_FINAL_CHECKLIST.md`

## 💡 Best Practices

1. **Always use types**: Define Props interfaces
2. **Handle errors**: Check response.success before using data
3. **Use constants**: Define API URLs in config
4. **Comment complex logic**: Add JSDoc comments
5. **Write tests**: Aim for 80%+ coverage
6. **Keep components small**: Easier to test and reuse
7. **Use utility functions**: Don't repeat code
8. **Mobile first**: Start with mobile styles

## 🚨 Before Committing

```bash
npm run type-check    # Check TypeScript
npm run test          # Run tests
npm run build         # Build for production
# Verify no errors in any of the above
```

## 🌐 API Base URL

Development: `http://localhost:8000`

Configure in `src/services/http_client.ts`:
```typescript
const API_BASE_URL = "http://localhost:8000";
```

Or use environment variable:
```bash
# .env
VITE_API_URL=http://localhost:8000
```

## 📞 Getting Help

1. Check `frontend/DEVELOPMENT.md` for detailed info
2. Search for similar code in existing components
3. Check test files for usage examples
4. Review mock data for expected formats

## 🎯 Key Dependencies

- **React 18**: UI framework
- **TypeScript**: Type safety
- **Vite**: Build tool
- **Vitest**: Test runner
- **Fetch API**: HTTP requests (built-in)

## ⚡ Performance Tips

1. Use `React.memo()` for expensive components
2. Use `useCallback()` for event handlers
3. Use `useMemo()` for expensive calculations
4. Lazy load pages with `React.lazy()`
5. Optimize images
6. Check bundle size regularly

## 🔐 Authentication

Token is automatically managed:
- Stored in localStorage
- Added to all requests
- Cleared on logout

```typescript
// Login
await authAPI.login(email, password);
// Token automatically saved and used for future requests

// Logout
await authAPI.logout();
// Token automatically cleared
```

---

**Last Updated**: December 2024  
**Version**: 1.0  
**Status**: Production Ready ✅
