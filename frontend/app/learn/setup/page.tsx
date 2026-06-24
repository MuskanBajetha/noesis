"use client";

import { Suspense } from "react";
import LearningSetupContent from "./LearningSetupContent";

export default function LearningSetupPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <LearningSetupContent />
    </Suspense>
  );
}