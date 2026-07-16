# Git Hooks for Security

This directory contains git hooks to prevent accidental commits of secrets and sensitive information.

## 🚀 Quick Start

Install the hooks by running:

```bash
bash scripts/git-hooks/install-hooks.sh
```

## 🔒 What Gets Blocked

The pre-commit hook prevents committing:

- **GitLab Personal Access Tokens** (glpat-xxxx)
- **GitHub Personal Access Tokens** (ghp_xxxx)
- **AWS Access Keys** (AKIA...)
- **Private Keys** (RSA, SSH, etc.)
- **JWT Tokens**
- **Hardcoded passwords**
- **API Keys**
- **Database connection strings with credentials**
- **Slack tokens**

## ⚠️ Warnings

The hook also warns about:
- Potential API keys
- Database connection strings
- Hardcoded passwords in common patterns

## 📐 Architecture Check

After the secret scan, the hook runs `scripts/check_forbidden_imports.py`, which blocks
the commit if `computor-types`, `computor-cli`, or `computor-client` import backend-only
packages (fastapi, sqlalchemy, `computor_backend`, …). Run it manually with
`python3 scripts/check_forbidden_imports.py`.

## 🛠️ Manual Installation

If the install script doesn't work, you can manually install:

```bash
cp scripts/git-hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## 🚨 Emergency Bypass

In rare cases where you need to bypass the hook (NOT RECOMMENDED):

```bash
git commit --no-verify -m "your message"
```

⚠️ **WARNING**: Only use this if you're absolutely sure there are no secrets in your commit!

## 🧪 Testing the Hook

To test if the hook is working, try to commit a file with a fake token:

```bash
echo 'TOKEN="glpat-EXAMPLE_1234567890abc"' > test-secret.py
git add test-secret.py
git commit -m "test" # This should fail with a real token
```

## 🤝 Contributing

When adding new secret patterns:

1. Edit `scripts/git-hooks/pre-commit`
2. Add your pattern to the `check_file()` function
3. Test thoroughly to avoid false positives
4. Update this README if needed

## 📋 Troubleshooting

**Hook not running?**
- Make sure it's executable: `chmod +x .git/hooks/pre-commit`
- Check if you have the `file` command installed (needed for binary detection)

**Too many false positives?**
- The hook warns about potential issues but only blocks definite secrets
- Use environment variables for all sensitive data
- For example tokens, use clear names like `EXAMPLE_TOKEN` or `YOUR_TOKEN_HERE`

**Hook is too slow?**
- The hook only checks staged files
- Binary files are automatically skipped
- Consider using `.gitignore` for large generated files

## 🔐 Best Practices

1. **Never commit real tokens** - Always use environment variables
2. **Use .env files** - Keep them in `.gitignore`
3. **Review warnings** - Even if the commit succeeds, check the warnings
4. **Update regularly** - New token formats emerge, keep the patterns updated