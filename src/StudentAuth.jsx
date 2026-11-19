import React, {useState} from 'react';
import {ArrowRight} from 'lucide-react';
import {studentApi} from './studentApi';

export default function StudentAuth({mode, language, onNavigate, onSuccess}) {
  const signup = mode === 'signup';
  const hi = language === 'hi';
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const action = signup ? (hi ? 'खाता बनाएँ' : 'Create account') : (hi ? 'साइन इन करें' : 'Sign in');

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const values = Object.fromEntries(new FormData(event.currentTarget));
      const {account} = await studentApi('/auth/' + mode, values);
      onSuccess(account);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return <section className="platform-panel student-auth">
    <h1>{action}</h1>
    <p>{signup ? (hi ? 'अपना अभ्यास और प्रगति सहेजें।' : 'Save your practice and track your progress.') :
      (hi ? 'स्कूल से मिला उपयोगकर्ता नाम और पासवर्ड यहाँ दर्ज करें।' : 'Use the username and password provided by your teacher, or sign in to your own account.')}</p>
    <form onSubmit={submit}>
      {signup && <label>{hi ? 'आपका नाम' : 'Display name'}<input name="display_name" autoComplete="nickname" required maxLength={80}/></label>}
      <label>{hi ? 'उपयोगकर्ता नाम' : 'Username'}<input name="username" autoComplete="username" required maxLength={40} pattern={signup ? '[A-Za-z0-9][A-Za-z0-9_\\-]{2,39}' : undefined}/></label>
      <label>{hi ? 'पासवर्ड' : 'Password'}<input type="password" name="password" autoComplete={signup ? 'new-password' : 'current-password'} required minLength={signup ? 12 : undefined} maxLength={128}/></label>
      {signup && <small>{hi ? 'पासवर्ड कम से कम 12 अक्षरों का रखें।' : 'Use at least 12 characters for your password.'}</small>}
      {error && <p className="alert danger" role="alert">{error}</p>}
      <button className="primary-button" disabled={busy}>{action}<ArrowRight size={17}/></button>
    </form>
    <button className="text-button" onClick={() => onNavigate(signup ? 'login' : 'signup')}>
      {signup ? (hi ? 'पहले से खाता है? साइन इन करें' : 'Already have an account? Sign in') :
        (hi ? 'नए विद्यार्थी हैं? खाता बनाएँ' : 'New student? Create an account')}
    </button>
  </section>;
}
