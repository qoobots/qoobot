<template>
  <footer class="app-footer">
    <div class="footer-inner">
      <div class="footer-section">
        <h4>QooBot Community</h4>
        <p>仿生人开发者社区</p>
        <p class="license">Apache-2.0 License</p>
      </div>
      <div class="footer-section">
        <h4>资源</h4>
        <a href="#">文档</a>
        <a href="#">API 参考</a>
        <a href="#">GitHub</a>
        <a href="#">论坛</a>
      </div>
      <div class="footer-section">
        <h4>社区</h4>
        <a href="#">贡献指南</a>
        <a href="#">行为准则</a>
        <a href="#">RFC 流程</a>
        <a href="#">路线图</a>
      </div>
      <div class="footer-section">
        <h4>联系我们</h4>
        <a href="#">Discord</a>
        <a href="#">GitHub Issues</a>
        <a href="#">admin@qoobot.ai</a>
      </div>
    </div>
  </footer>
</template>

<style lang="scss" scoped>
.app-footer {
  background: #1A1A2E;
  color: #fff;
  margin-top: 48px;
  padding: 40px 20px;
}

.footer-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 40px;
}

.footer-section {
  h4 {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 12px;
    opacity: 0.9;
  }

  p {
    font-size: 13px;
    opacity: 0.6;
    line-height: 1.6;
  }

  .license { margin-top: 8px; }

  a {
    display: block;
    font-size: 13px;
    opacity: 0.6;
    margin-bottom: 8px;
    color: #fff;
    text-decoration: none;
    transition: opacity 0.2s;

    &:hover { opacity: 1; text-decoration: none; }
  }
}
</style>
