/**
 * Bundle Size Check Script
 * Analyzes Next.js build output and reports bundle sizes
 * 
 * Usage: node scripts/bundle-size.js
 * or: npm run bundle-size
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');

const SIZE_THRESHOLDS = {
  // Page chunks (KB)
  'page': 150,      // Individual page chunks should be under 150KB
  // Static files (KB)  
  'static': 250,    // Static file chunks should be under 250KB
  // Total JS (KB)
  'total': 500,     // Total JS should be under 500KB
};

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function analyzeBuild() {
  const buildDir = path.join(rootDir, '.next');
  const analysis = {
    pages: [],
    static: [],
    totalJs: 0,
    warnings: [],
  };

  // Check if build directory exists
  if (!fs.existsSync(buildDir)) {
    console.log('⚠️  Build directory not found. Run "npm run build" first.');
    console.log('   Skipping bundle analysis.');
    return analysis;
  }

  // Analyze app directory pages
  const appDir = path.join(buildDir, 'app');
  if (fs.existsSync(appDir)) {
    analyzeDirectory(appDir, 'page', analysis);
  }

  // Analyze static directory
  const staticDir = path.join(buildDir, 'static');
  if (fs.existsSync(staticDir)) {
    analyzeDirectory(staticDir, 'static', analysis);
  }

  // Analyze chunks directory
  const chunksDir = path.join(buildDir, 'chunks');
  if (fs.existsSync(chunksDir)) {
    analyzeDirectory(chunksDir, 'static', analysis);
  }

  return analysis;
}

function analyzeDirectory(dir, type, analysis) {
  try {
    const files = getAllFiles(dir);
    
    files.forEach(file => {
      const stats = fs.statSync(file);
      const relativePath = path.relative(dir, file);
      const size = stats.size;
      
      const entry = {
        path: relativePath,
        size,
        formatted: formatBytes(size),
      };

      if (type === 'page') {
        analysis.pages.push(entry);
      } else {
        analysis.static.push(entry);
      }

      analysis.totalJs += size;

      // Check thresholds
      const threshold = SIZE_THRESHOLDS[type];
      if (threshold && size > threshold * 1024) {
        analysis.warnings.push(
          `${entry.path} (${entry.formatted}) exceeds ${threshold}KB threshold`
        );
      }
    });
  } catch (err) {
    console.warn(`Warning: Could not analyze ${dir}: ${err.message}`);
  }
}

function getAllFiles(dir) {
  const files = [];
  
  if (!fs.existsSync(dir)) return files;
  
  const items = fs.readdirSync(dir);
  
  items.forEach(item => {
    const fullPath = path.join(dir, item);
    const stats = fs.statSync(fullPath);
    
    if (stats.isDirectory()) {
      files.push(...getAllFiles(fullPath));
    } else if (fullPath.endsWith('.js') || fullPath.endsWith('.js.br') || fullPath.endsWith('.js.gz')) {
      files.push(fullPath);
    }
  });
  
  return files;
}

function printReport(analysis) {
  console.log('\n📦 Bundle Size Report\n');
  console.log('=' .repeat(60));

  if (analysis.pages.length > 0) {
    console.log('\n📄 Page Chunks:');
    analysis.pages
      .sort((a, b) => b.size - a.size)
      .slice(0, 10)
      .forEach(page => {
        console.log(`  ${page.path.padEnd(40)} ${page.formatted.padStart(10)}`);
      });
  }

  if (analysis.static.length > 0) {
    console.log('\n📁 Static Files:');
    analysis.static
      .sort((a, b) => b.size - a.size)
      .slice(0, 10)
      .forEach(file => {
        console.log(`  ${file.path.padEnd(40)} ${file.formatted.padStart(10)}`);
      });
  }

  console.log('\n📊 Summary:');
  console.log(`  Total JS Size: ${formatBytes(analysis.totalJs)}`);
  console.log(`  Total Files: ${analysis.pages.length + analysis.static.length}`);

  if (analysis.warnings.length > 0) {
    console.log('\n⚠️  Warnings (exceeds threshold):');
    analysis.warnings.forEach(w => console.log(`  - ${w}`));
  } else {
    console.log('\n✅ All bundle sizes within thresholds');
  }

  console.log('=' .repeat(60) + '\n');
}

// Run analysis
const analysis = analyzeBuild();
printReport(analysis);

// Exit with warning if thresholds exceeded
if (analysis.warnings.length > 0) {
  console.log('⚠️  Bundle size warnings detected. Consider optimizing.');
  process.exit(1);
} else {
  console.log('✅ Bundle sizes are optimal.');
  process.exit(0);
}