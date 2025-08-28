# Contributing to AndroidZen Pro - Frontend

**Copyright © 2024 Aniket. All rights reserved.**

Thank you for your interest in contributing to AndroidZen Pro Frontend! This document provides guidelines and instructions for contributing to this proprietary project.

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Standards](#code-standards)
- [Contribution Process](#contribution-process)
- [Issue Reporting](#issue-reporting)
- [Security Considerations](#security-considerations)
- [License and Legal](#license-and-legal)

## 🚀 Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Node.js 18.0+** and **npm 8.0+** installed
- **Git** for version control
- **Modern IDE** with TypeScript support (VS Code recommended)
- **Access permissions** from the project owner
- Familiarity with **React**, **TypeScript**, and **Material-UI**

### Repository Access

This is a **proprietary project**. Contributors must:

1. **Obtain explicit written permission** from Aniket (project owner)
2. **Sign a Contributor License Agreement (CLA)** before submitting code
3. **Respect confidentiality** and proprietary information
4. **Follow all security protocols** and guidelines

## 🛠️ Development Setup

### Initial Setup

1. **Clone the repository** (requires access):
   ```bash
   git clone https://github.com/your-org/androidzen-pro.git
   cd androidzen-pro/frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Environment configuration**:
   ```bash
   cp .env.example .env.local
   # Configure your local environment variables
   ```

4. **Start development server**:
   ```bash
   npm start
   ```

### Development Environment

- **IDE Setup**: VS Code with recommended extensions:
  - ES7+ React/Redux/React-Native snippets
  - TypeScript Hero
  - Prettier - Code formatter
  - ESLint
  - Auto Rename Tag
  - Bracket Pair Colorizer

- **Browser Extensions** for testing:
  - React Developer Tools
  - Redux DevTools (if applicable)

## 📝 Code Standards

### TypeScript Guidelines

- **Strict Mode**: All TypeScript files must pass strict mode compilation
- **Type Definitions**: Provide explicit types for all function parameters and returns
- **Interface Usage**: Use interfaces for object types, types for unions/primitives
- **Generic Types**: Use generics appropriately for reusable components

```typescript
// ✅ Good
interface DeviceProps {
  id: string;
  name: string;
  status: DeviceStatus;
  onStatusChange: (status: DeviceStatus) => void;
}

const DeviceCard: React.FC<DeviceProps> = ({ id, name, status, onStatusChange }) => {
  // Component implementation
};

// ❌ Avoid
const DeviceCard = (props: any) => {
  // Implementation
};
```

### React Component Standards

- **Functional Components**: Use functional components with hooks
- **Component Structure**: Follow consistent component organization
- **Props Interface**: Define clear props interfaces
- **State Management**: Use appropriate state management (local vs global)

```typescript
// Component structure template
import React, { useState, useEffect, useCallback } from 'react';
import { Box, Card, Typography } from '@mui/material';
import { ComponentProps } from '../types';

interface LocalComponentProps {
  // Props definition
}

export const ComponentName: React.FC<LocalComponentProps> = ({
  prop1,
  prop2,
}) => {
  // Hooks
  const [state, setState] = useState<StateType>(initialState);
  
  // Event handlers
  const handleAction = useCallback(() => {
    // Implementation
  }, [dependencies]);
  
  // Effects
  useEffect(() => {
    // Side effects
  }, [dependencies]);
  
  // Render
  return (
    <Box>
      {/* JSX content */}
    </Box>
  );
};

export default ComponentName;
```

### Styling Guidelines

- **Material-UI Theme**: Use theme values for consistency
- **CSS-in-JS**: Prefer Material-UI's styling solutions
- **Responsive Design**: Implement mobile-first responsive design
- **Accessibility**: Follow WCAG 2.1 AA standards

```typescript
// ✅ Good - Using theme and responsive design
import { styled } from '@mui/material/styles';
import { Box } from '@mui/material';

const StyledContainer = styled(Box)(({ theme }) => ({
  padding: theme.spacing(2),
  backgroundColor: theme.palette.background.paper,
  borderRadius: theme.shape.borderRadius,
  [theme.breakpoints.down('sm')]: {
    padding: theme.spacing(1),
  },
}));
```

### Code Formatting

- **Prettier**: All code must be formatted with Prettier
- **ESLint**: Follow ESLint configuration without warnings
- **Import Order**: Organize imports consistently

```typescript
// Import order
import React from 'react'; // React imports
import { useState, useEffect } from 'react'; // React hooks
import { Box, Button } from '@mui/material'; // External libraries
import { CustomComponent } from '../components'; // Internal components
import { ApiService } from '../services'; // Internal services
import { ComponentProps } from '../types'; // Type imports
import './Component.css'; // Style imports
```

## 🔄 Contribution Process

### Workflow Overview

1. **Permission**: Obtain written permission from project owner
2. **Branch Creation**: Create feature branch from main
3. **Development**: Implement changes following guidelines
4. **Testing**: Ensure all tests pass and add new tests
5. **Review**: Submit for internal code review
6. **Integration**: Merge after approval

### Branch Naming Convention

```bash
# Feature branches
feature/device-management-ui
feature/real-time-charts

# Bug fixes
fix/websocket-connection-issue
fix/performance-chart-rendering

# Security updates
security/auth-token-validation
security/xss-prevention

# Documentation
docs/api-documentation-update
docs/deployment-guide
```

### Commit Message Format

Follow conventional commits format:

```bash
# Format
<type>(<scope>): <subject>

<body>

<footer>

# Examples
feat(dashboard): add real-time device monitoring
fix(auth): resolve token refresh infinite loop
docs(readme): update installation instructions
security(api): implement input validation
test(components): add unit tests for DeviceCard
```

### Pull Request Guidelines

**Before submitting:**

- [ ] All tests pass (`npm test`)
- [ ] Code is properly formatted (`npm run format`)
- [ ] No ESLint errors (`npm run lint`)
- [ ] TypeScript compilation successful (`npm run type-check`)
- [ ] Security audit passes (`npm run security:scan`)
- [ ] Documentation updated if needed

**Pull Request Template:**

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Cross-browser testing done

## Security Considerations
- [ ] No sensitive data exposed
- [ ] Input validation implemented
- [ ] Authentication/authorization respected
- [ ] Security best practices followed

## Screenshots (if applicable)
Add screenshots for UI changes

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

## 🐛 Issue Reporting

### Security Issues

**CRITICAL**: Security vulnerabilities must be reported privately to the project owner immediately. Do not create public issues for security problems.

**Contact**: Repository owner through secure channels

### Bug Reports

```markdown
## Bug Report Template

### Description
Clear description of the bug

### Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. See error

### Expected Behavior
What you expected to happen

### Actual Behavior
What actually happened

### Environment
- OS: [e.g., Windows 10, macOS 12.0]
- Browser: [e.g., Chrome 95.0, Firefox 94.0]
- Node.js Version: [e.g., 18.12.0]
- npm Version: [e.g., 8.19.0]

### Additional Context
Screenshots, error logs, etc.
```

### Feature Requests

```markdown
## Feature Request Template

### Summary
Brief summary of the feature

### Motivation
Why is this feature needed?

### Detailed Description
Detailed description of the proposed feature

### Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

### Additional Context
Mockups, examples, references
```

## 🔒 Security Considerations

### Code Security

- **Input Validation**: Validate all user inputs
- **XSS Prevention**: Sanitize data before rendering
- **CSRF Protection**: Implement CSRF tokens for state-changing operations
- **Authentication**: Respect authentication boundaries
- **Authorization**: Check user permissions appropriately

### Data Handling

- **Sensitive Data**: Never log or expose sensitive information
- **API Keys**: Use environment variables for configuration
- **Personal Data**: Handle personal data according to privacy policies
- **Encryption**: Use appropriate encryption for data transmission

### Dependencies

- **Security Audits**: Run `npm audit` before submissions
- **Dependency Updates**: Keep dependencies updated
- **Known Vulnerabilities**: Address security advisories promptly

## ⚖️ License and Legal

### Proprietary License

This project is under **proprietary license**. All contributions become property of the project owner (Aniket).

### Contributor License Agreement (CLA)

All contributors must sign a CLA before contributing:

1. **Individual CLA**: For individual contributors
2. **Corporate CLA**: For company employees
3. **Legal Review**: All contributions subject to legal review

### Intellectual Property

- **Code Ownership**: All contributed code becomes proprietary to project owner
- **Original Work**: Contributors must certify code is original work
- **Third-party Code**: Explicitly declare any third-party code inclusion
- **License Compatibility**: Ensure any dependencies are license-compatible

### Confidentiality

- **Non-disclosure**: Treat all project information as confidential
- **Public Discussion**: Avoid discussing proprietary features publicly
- **Code Sharing**: Do not share code outside authorized channels

## 📞 Getting Help

### Support Channels

1. **Internal Documentation**: Check project documentation first
2. **Team Chat**: Use designated communication channels
3. **Direct Contact**: Contact project owner for urgent issues
4. **Code Review**: Use pull request discussions for code questions

### Contact Information

- **Project Owner**: Aniket
- **Repository**: https://github.com/@DevAniketIT/androidzen-pro
- **Security Issues**: Private communication channels only

---

## 📝 Additional Resources

- [React Documentation](https://reactjs.org/docs)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Material-UI Documentation](https://mui.com/)
- [Testing Library Documentation](https://testing-library.com/)

**Copyright © 2024 Aniket. All rights reserved.**

---

*By contributing to this project, you acknowledge that you have read and agree to the terms outlined in this document and the project's LICENSE file.*
