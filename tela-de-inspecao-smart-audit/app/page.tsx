import { InspectionProvider, InspectionForm } from '@/components/inspection'

export default function Home() {
  return (
    <InspectionProvider>
      <InspectionForm />
    </InspectionProvider>
  )
}
