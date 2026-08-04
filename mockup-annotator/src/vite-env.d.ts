/// <reference types="vite/client" />

// OpenCV.js attaches its module to window.cv once ready.
declare global {
  interface Window {
    cv?: any;
  }
}
export {};
