import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '../stores/auth'
import { Zap, User, Mail, Lock, Eye, EyeOff, AlertCircle, ArrowRight, Loader2, Check, X } from 'lucide-react'
import clsx from 'clsx'

export default function RegisterPage() {
  const navigate = useNavigate()
  const { register, isLoading, error, clearError } = useAuthStore()
  const [showPassword, setShowPassword] = useState(false)
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    displayName: '',
  })
  const [touched, setTouched] = useState({
    username: false,
    email: false,
    password: false,
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()
    
    try {
      await register(
        formData.username,
        formData.email,
        formData.password,
        formData.displayName || undefined
      )
      navigate('/chat')
    } catch {
      // Error handled by store
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
    if (error) clearError()
  }

  const handleBlur = (field: string) => {
    setTouched((prev) => ({ ...prev, [field]: true }))
  }

  // Validation
  const validations = {
    username: formData.username.length >= 3,
    email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email),
    passwordLength: formData.password.length >= 6,
  }

  const isValid = validations.username && validations.email && validations.passwordLength

  return (
    <div className="min-h-screen flex items-center justify-center p-4 auth-bg">
      {/* Decorative elements */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-accent-purple/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent-cyan/10 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] pattern-dots opacity-30" />
      </div>

      <div className="w-full max-w-md relative animate-fade-in">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-accent-purple to-accent-cyan shadow-lg shadow-accent-purple/30 mb-4">
            <Zap className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-display font-bold gradient-text">Agent Bot</h1>
          <p className="text-text-secondary mt-2">Create your account</p>
        </div>

        {/* Form Card */}
        <div className="bg-bg-secondary/80 backdrop-blur-xl border border-white/5 rounded-2xl p-8 shadow-xl">
          <h2 className="text-xl font-semibold mb-6">Get Started</h2>

          {error && (
            <div className="mb-6 p-4 rounded-xl bg-accent-red/10 border border-accent-red/30 text-accent-red flex items-start gap-3 animate-slide-down">
              <AlertCircle size={20} className="flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Registration Failed</p>
                <p className="text-sm opacity-80 mt-0.5">{error}</p>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Username */}
            <div className="space-y-2">
              <label htmlFor="username" className="block text-sm font-medium text-text-secondary">
                Username <span className="text-accent-red">*</span>
              </label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary">
                  <User size={18} />
                </div>
                <input
                  id="username"
                  name="username"
                  type="text"
                  value={formData.username}
                  onChange={handleChange}
                  onBlur={() => handleBlur('username')}
                  placeholder="Choose a username"
                  className={clsx(
                    'input pl-10',
                    touched.username && !validations.username && 'border-accent-red/50 focus:border-accent-red'
                  )}
                  autoComplete="username"
                />
                {touched.username && formData.username && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    {validations.username ? (
                      <Check size={18} className="text-accent-green" />
                    ) : (
                      <X size={18} className="text-accent-red" />
                    )}
                  </div>
                )}
              </div>
              {touched.username && !validations.username && formData.username && (
                <p className="text-xs text-accent-red">Username must be at least 3 characters</p>
              )}
            </div>

            {/* Email */}
            <div className="space-y-2">
              <label htmlFor="email" className="block text-sm font-medium text-text-secondary">
                Email <span className="text-accent-red">*</span>
              </label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary">
                  <Mail size={18} />
                </div>
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  onBlur={() => handleBlur('email')}
                  placeholder="your@email.com"
                  className={clsx(
                    'input pl-10',
                    touched.email && !validations.email && 'border-accent-red/50 focus:border-accent-red'
                  )}
                  autoComplete="email"
                />
                {touched.email && formData.email && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    {validations.email ? (
                      <Check size={18} className="text-accent-green" />
                    ) : (
                      <X size={18} className="text-accent-red" />
                    )}
                  </div>
                )}
              </div>
              {touched.email && !validations.email && formData.email && (
                <p className="text-xs text-accent-red">Please enter a valid email address</p>
              )}
            </div>

            {/* Display Name */}
            <div className="space-y-2">
              <label htmlFor="displayName" className="block text-sm font-medium text-text-secondary">
                Display Name <span className="text-text-tertiary">(optional)</span>
              </label>
              <input
                id="displayName"
                name="displayName"
                type="text"
                value={formData.displayName}
                onChange={handleChange}
                placeholder="How should we call you?"
                className="input"
              />
            </div>

            {/* Password */}
            <div className="space-y-2">
              <label htmlFor="password" className="block text-sm font-medium text-text-secondary">
                Password <span className="text-accent-red">*</span>
              </label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary">
                  <Lock size={18} />
                </div>
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={handleChange}
                  onBlur={() => handleBlur('password')}
                  placeholder="Create a password"
                  className="input pl-10 pr-10"
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-tertiary hover:text-text-secondary transition-colors"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>

              {/* Password Requirements */}
              <div className="mt-3 space-y-1.5">
                <PasswordRequirement 
                  met={validations.passwordLength} 
                  text="At least 6 characters" 
                />
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={!isValid || isLoading}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-gradient-to-r from-accent-purple to-accent-cyan text-white font-medium transition-all duration-200 hover:opacity-90 hover:shadow-lg hover:shadow-accent-purple/20 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Creating account...
                </>
              ) : (
                <>
                  Create Account
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-text-secondary">
              Already have an account?{' '}
              <Link
                to="/login"
                className="text-accent-purple hover:text-accent-cyan font-medium transition-colors"
              >
                Sign in
              </Link>
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-text-tertiary text-sm mt-6">
          By creating an account, you agree to our Terms of Service
        </p>
      </div>
    </div>
  )
}

function PasswordRequirement({ met, text }: { met: boolean; text: string }) {
  return (
    <div className={clsx(
      'flex items-center gap-2 text-xs transition-colors',
      met ? 'text-accent-green' : 'text-text-tertiary'
    )}>
      {met ? <Check size={14} /> : <X size={14} />}
      <span>{text}</span>
    </div>
  )
}
