#!/usr/bin/env node

/**
 * Security Audit Script for AndroidZen Pro Frontend
 * Performs comprehensive security checks on the codebase
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

class SecurityAuditor {
  constructor() {
    this.issues = [];
    this.warnings = [];
    this.srcDir = path.join(__dirname, '../src');
    this.publicDir = path.join(__dirname, '../public');
    this.staticDir = path.join(__dirname, '../static');
  }

  log(message, type = 'INFO') {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] ${type}: ${message}`);
  }

  error(message) {
    this.log(message, 'ERROR');
    this.issues.push(message);
  }

  warn(message) {
    this.log(message, 'WARN');
    this.warnings.push(message);
  }

  success(message) {
    this.log(message, 'PASS');
  }

  /**
   * Check for hardcoded secrets, API keys, tokens
   */
  checkForHardcodedSecrets() {
    this.log('Checking for hardcoded secrets...');
    
    const secretPatterns = [
      /(?:password|pwd)\s*[=:]\s*["'][^"']{8,}["']/gi,
      /(?:api[_-]?key|apikey)\s*[=:]\s*["'][^"']{20,}["']/gi,
      /(?:secret[_-]?key|secretkey)\s*[=:]\s*["'][^"']{20,}["']/gi,
      /(?:access[_-]?token|accesstoken)\s*[=:]\s*["'][^"']{20,}["']/gi,
      /(?:auth[_-]?token|authtoken)\s*[=:]\s*["'][^"']{20,}["']/gi,
      /(?:bearer)\s+[a-zA-Z0-9_-]{20,}/gi,
      /sk-[a-zA-Z0-9]{20,}/g, // OpenAI API keys
      /AIza[a-zA-Z0-9_-]{35}/g, // Google API keys
      /AKIA[A-Z0-9]{16}/g, // AWS Access Keys
    ];

    const checkFile = (filePath) => {
      try {
        const content = fs.readFileSync(filePath, 'utf8');
        secretPatterns.forEach((pattern, index) => {
          const matches = content.match(pattern);
          if (matches) {
            this.error(`Potential hardcoded secret found in ${filePath}: ${matches[0].substring(0, 50)}...`);
          }
        });
      } catch (err) {
        this.warn(`Could not read file ${filePath}: ${err.message}`);
      }
    };

    this.walkDirectory(this.srcDir, checkFile, /\.(js|jsx|ts|tsx)$/);
    this.walkDirectory(this.staticDir, checkFile, /\.(js|jsx|ts|tsx)$/);
    
    this.success('Hardcoded secrets check completed');
  }

  /**
   * Check for development configurations in production build
   */
  checkDevConfigurations() {
    this.log('Checking for development configurations...');
    
    const devPatterns = [
      /console\.log\(/g,
      /console\.debug\(/g,
      /console\.warn\(/g,
      /debugger\s*;/g,
      /localhost/g,
      /127\.0\.0\.1/g,
    ];

    if (process.env.NODE_ENV === 'production') {
      const checkFile = (filePath) => {
        try {
          const content = fs.readFileSync(filePath, 'utf8');
          devPatterns.forEach(pattern => {
            if (pattern.test(content)) {
              this.warn(`Development code found in production build: ${filePath}`);
            }
          });
        } catch (err) {
          this.warn(`Could not read file ${filePath}: ${err.message}`);
        }
      };

      this.walkDirectory(path.join(__dirname, '../build'), checkFile, /\.(js|css)$/);
    }
    
    this.success('Development configurations check completed');
  }

  /**
   * Check for sensitive data in logs
   */
  checkSensitiveLogging() {
    this.log('Checking for sensitive data in logging...');
    
    const sensitivePatterns = [
      /console\.log.*(?:password|token|secret|key)/gi,
      /console\.debug.*(?:password|token|secret|key)/gi,
      /console\.error.*(?:password|token|secret|key)/gi,
    ];

    const checkFile = (filePath) => {
      try {
        const content = fs.readFileSync(filePath, 'utf8');
        sensitivePatterns.forEach(pattern => {
          const matches = content.match(pattern);
          if (matches) {
            this.error(`Sensitive data potentially logged in ${filePath}: ${matches[0]}`);
          }
        });
      } catch (err) {
        this.warn(`Could not read file ${filePath}: ${err.message}`);
      }
    };

    this.walkDirectory(this.srcDir, checkFile, /\.(js|jsx|ts|tsx)$/);
    
    this.success('Sensitive logging check completed');
  }

  /**
   * Check environment configuration
   */
  checkEnvironmentConfiguration() {
    this.log('Checking environment configuration...');
    
    // Check if .env.example exists
    const envExamplePath = path.join(__dirname, '../.env.example');
    if (!fs.existsSync(envExamplePath)) {
      this.error('.env.example file is missing');
    } else {
      this.success('.env.example file exists');
    }

    // Check if .env is gitignored
    const gitignorePath = path.join(__dirname, '../../.gitignore');
    if (fs.existsSync(gitignorePath)) {
      const gitignoreContent = fs.readFileSync(gitignorePath, 'utf8');
      if (gitignoreContent.includes('.env')) {
        this.success('.env files are properly gitignored');
      } else {
        this.error('.env files are not gitignored');
      }
    } else {
      this.warn('.gitignore file not found');
    }
  }

  /**
   * Check for insecure HTTP requests
   */
  checkInsecureRequests() {
    this.log('Checking for insecure HTTP requests...');
    
    const insecurePatterns = [
      /http:\/\/(?!localhost|127\.0\.0\.1)/gi,
      /ws:\/\/(?!localhost|127\.0\.0\.1)/gi,
    ];

    const checkFile = (filePath) => {
      try {
        const content = fs.readFileSync(filePath, 'utf8');
        insecurePatterns.forEach(pattern => {
          const matches = content.match(pattern);
          if (matches) {
            this.warn(`Insecure HTTP/WS request found in ${filePath}: ${matches[0]}`);
          }
        });
      } catch (err) {
        this.warn(`Could not read file ${filePath}: ${err.message}`);
      }
    };

    this.walkDirectory(this.srcDir, checkFile, /\.(js|jsx|ts|tsx)$/);
    
    this.success('Insecure requests check completed');
  }

  /**
   * Check dependencies for vulnerabilities
   */
  checkDependencyVulnerabilities() {
    this.log('Checking dependencies for vulnerabilities...');
    
    try {
      const auditOutput = execSync('npm audit --json', { encoding: 'utf8' });
      const auditResult = JSON.parse(auditOutput);
      
      if (auditResult.metadata.vulnerabilities.total > 0) {
        this.error(`Found ${auditResult.metadata.vulnerabilities.total} dependency vulnerabilities`);
        
        Object.entries(auditResult.metadata.vulnerabilities).forEach(([severity, count]) => {
          if (count > 0 && severity !== 'total') {
            this.warn(`${severity.toUpperCase()}: ${count} vulnerabilities`);
          }
        });
      } else {
        this.success('No dependency vulnerabilities found');
      }
    } catch (err) {
      this.warn(`Could not run npm audit: ${err.message}`);
    }
  }

  /**
   * Walk directory recursively and apply callback to matching files
   */
  walkDirectory(dir, callback, pattern = null) {
    if (!fs.existsSync(dir)) return;
    
    const files = fs.readdirSync(dir);
    
    files.forEach(file => {
      const filePath = path.join(dir, file);
      const stat = fs.statSync(filePath);
      
      if (stat.isDirectory()) {
        if (!file.startsWith('.') && file !== 'node_modules') {
          this.walkDirectory(filePath, callback, pattern);
        }
      } else if (!pattern || pattern.test(file)) {
        callback(filePath);
      }
    });
  }

  /**
   * Generate security report
   */
  generateReport() {
    const timestamp = new Date().toISOString();
    const report = {
      timestamp,
      summary: {
        issues: this.issues.length,
        warnings: this.warnings.length,
        status: this.issues.length === 0 ? 'PASS' : 'FAIL'
      },
      issues: this.issues,
      warnings: this.warnings
    };

    // Write report to file
    const reportPath = path.join(__dirname, '../security-audit-report.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    
    // Log summary
    this.log('='.repeat(60));
    this.log('SECURITY AUDIT SUMMARY');
    this.log('='.repeat(60));
    this.log(`Status: ${report.summary.status}`);
    this.log(`Issues: ${report.summary.issues}`);
    this.log(`Warnings: ${report.summary.warnings}`);
    this.log(`Report saved to: ${reportPath}`);
    
    return report.summary.status === 'PASS' ? 0 : 1;
  }

  /**
   * Run all security checks
   */
  run() {
    this.log('Starting security audit...');
    
    this.checkForHardcodedSecrets();
    this.checkDevConfigurations();
    this.checkSensitiveLogging();
    this.checkEnvironmentConfiguration();
    this.checkInsecureRequests();
    this.checkDependencyVulnerabilities();
    
    return this.generateReport();
  }
}

// Run audit if called directly
if (require.main === module) {
  const auditor = new SecurityAuditor();
  const exitCode = auditor.run();
  process.exit(exitCode);
}

module.exports = SecurityAuditor;
