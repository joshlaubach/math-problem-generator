/**
 * Login page - User authentication
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthUser } from "../hooks/useAuthUser";
import "./LoginPage.css";

export function LoginPage() {
  const navigate = useNavigate();
  const { login, error, clearError } = useAuthUser();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    // Validation
    if (!email.trim()) {
      setLocalError("Please enter your email");
      return;
    }

    if (!password) {
      setLocalError("Please enter your password");
      return;
    }

    try {
      setIsLoading(true);
      const response = await login(email, password);

      // Redirect based on role (this happens via login() updating state)
      // For now, navigate to student dashboard - will be redirected by App if teacher
      navigate("/");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Login failed";
      setLocalError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const displayError = localError || error;

  return (
    <div className="login-page">
      <div className="login-container">
        <h1>Login</h1>

        {displayError && <div className="error-message">{displayError}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              disabled={isLoading}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              disabled={isLoading}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={isLoading}
          >
            {isLoading ? "Logging in..." : "Login"}
          </button>
        </form>

        <div className="login-footer">
          <p>
            Don't have an account?{" "}
            <a href="/register" onClick={(e) => {
              e.preventDefault();
              navigate("/register");
            }}>
              Register here
            </a>
          </p>
          <p>
            Want to practice as an anonymous student?{" "}
            <a href="/" onClick={(e) => {
              e.preventDefault();
              navigate("/");
            }}>
              Back to home
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
