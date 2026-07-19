import { redirect } from 'next/navigation';

// The lecturer view has no landing page of its own — the sidebar links straight
// to the sub-pages, so a direct hit on /lecturer lands on the first of them.
export default async function LecturerIndexPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  redirect(`/courses/${id}/lecturer/grading`);
}
