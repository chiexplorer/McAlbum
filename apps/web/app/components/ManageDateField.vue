<script setup lang="ts">
import { beijingToday } from '~/utils/manage-date'

const props = defineProps<{
  modelValue: string
  label: string
}>()

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const year = ref('')
const month = ref('')
const day = ref('')

const currentYear = Number(beijingToday().slice(0, 4))
const years = Array.from({ length: currentYear - 2009 + 6 }, (_, index) => String(currentYear + 5 - index))
const months = Array.from({ length: 12 }, (_, index) => String(index + 1).padStart(2, '0'))
const daysInMonth = computed(() => {
  if (!year.value || !month.value) return 31
  return new Date(Number(year.value), Number(month.value), 0).getDate()
})
const days = computed(() => Array.from(
  { length: daysInMonth.value },
  (_, index) => String(index + 1).padStart(2, '0'),
))

function composeValue(): string {
  return year.value && month.value && day.value
    ? `${year.value}-${month.value}-${day.value}`
    : ''
}

watch(() => props.modelValue, (value) => {
  if (value === composeValue()) return
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  year.value = match?.[1] ?? ''
  month.value = match?.[2] ?? ''
  day.value = match?.[3] ?? ''
}, { immediate: true })

watch([year, month, day], () => {
  if (Number(day.value) > daysInMonth.value) {
    day.value = String(daysInMonth.value).padStart(2, '0')
    return
  }
  const value = composeValue()
  if (value !== props.modelValue) emit('update:modelValue', value)
})
</script>

<template>
  <fieldset class="manage-date">
    <legend>{{ label }}</legend>
    <label>年
      <select v-model="year" aria-label="年" required>
        <option value="" disabled>年份</option>
        <option v-for="value in years" :key="value" :value="value">{{ value }}</option>
      </select>
    </label>
    <label>月
      <select v-model="month" aria-label="月" required>
        <option value="" disabled>月份</option>
        <option v-for="value in months" :key="value" :value="value">{{ Number(value) }} 月</option>
      </select>
    </label>
    <label>日
      <select v-model="day" aria-label="日" required>
        <option value="" disabled>日期</option>
        <option v-for="value in days" :key="value" :value="value">{{ Number(value) }} 日</option>
      </select>
    </label>
  </fieldset>
</template>
