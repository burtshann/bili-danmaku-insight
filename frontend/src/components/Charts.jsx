import { useMemo } from "react";

import EChart from "./EChart";


const palette = {
  ink: "#202329",
  cyan: "#11a8c5",
  pink: "#fb7299",
  green: "#38a169",
  grid: "#e7e9ee",
};

export function KeywordChart({ items = [] }) {
  const option = useMemo(() => ({
    animationDuration: 500,
    grid: { left: 12, right: 18, top: 16, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: {
      type: "value",
      axisLabel: { color: "#666b75" },
      splitLine: { lineStyle: { color: palette.grid } },
    },
    yAxis: {
      type: "category",
      inverse: true,
      data: items.slice(0, 10).map((item) => item.word),
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: palette.ink, width: 86, overflow: "truncate" },
    },
    series: [{
      type: "bar",
      data: items.slice(0, 10).map((item) => item.count),
      barMaxWidth: 18,
      itemStyle: { color: palette.cyan, borderRadius: [0, 3, 3, 0] },
    }],
  }), [items]);

  return <EChart option={option} ariaLabel="高频关键词柱状图" />;
}

export function TimelineChart({ items = [], peaks = [] }) {
  const option = useMemo(() => ({
    animationDuration: 500,
    grid: { left: 14, right: 18, top: 24, bottom: 28, containLabel: true },
    tooltip: {
      trigger: "axis",
      formatter(params) {
        const point = params[0];
        const item = items[point.dataIndex];
        return `${item.start}s - ${item.end}s<br/>弹幕 ${point.data[1]} 条`;
      },
    },
    xAxis: {
      type: "value",
      min: 0,
      max: items.at(-1)?.end || 1,
      minInterval: 1,
      axisLabel: {
        color: "#666b75",
        formatter: (value) => `${value}s`,
      },
      axisLine: { lineStyle: { color: "#ccd0d7" } },
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      axisLabel: { color: "#666b75" },
      splitLine: { lineStyle: { color: palette.grid } },
    },
    series: [{
      type: "line",
      smooth: 0.25,
      symbol: "none",
      data: items.map((item) => [item.start, item.count]),
      lineStyle: { width: 2, color: palette.pink },
      areaStyle: { color: "rgba(251, 114, 153, 0.13)" },
      markArea: {
        silent: true,
        itemStyle: { color: "rgba(56, 161, 105, 0.10)" },
        data: peaks.slice(0, 5).map((item) => [
          { xAxis: item.start },
          { xAxis: item.end },
        ]),
      },
    }],
  }), [items, peaks]);

  return <EChart option={option} ariaLabel="弹幕密度时间轴折线图" />;
}
