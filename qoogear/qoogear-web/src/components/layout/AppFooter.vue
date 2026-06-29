<template>
  <div class="footer">
    &copy; {{ year }} QooBot — Made for QooBot (MFQ) Certification Program. All rights reserved.
  </div>
</template>

<script setup lang="ts">
const year = new Date().getFullYear()
</script>
