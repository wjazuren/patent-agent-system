<template>
  <div class="patent-image-preview">
    <div class="image-title">{{ imageTitle }}</div>
    <div class="img-box">
      <img :src="imgSrc" alt="专利附图" loading="lazy" />
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  imgSrc: string
  imageTitle: string
}>()
</script>

<style lang="scss" scoped>
.patent-image-preview {
  margin: 16px 0;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fafafa;
}
.image-title {
  font-size: 14px;
  color: #333;
  margin-bottom: 10px;
  font-weight: 500;
}
.img-box {
  width: 100%;
  overflow: auto;
  text-align: center;
}
.img-box img {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
}
</style>