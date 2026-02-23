import Link from 'next/link';

interface NotFoundProps {
  title?: string;
  message?: string;
  showBackButton?: boolean;
  backLink?: string;
  backText?: string;
}

export default function NotFound({
  title = '404 - Not Found',
  message = 'The page you are looking for does not exist or you do not have permission to access it.',
  showBackButton = true,
  backLink = '/dashboard',
  backText = 'Go to Dashboard',
}: NotFoundProps) {
  return (
    <div className="min-h-[60vh] flex items-center justify-center p-6">
      <div className="max-w-md w-full text-center space-y-6">
        {/* 404 Icon */}
        <div className="flex justify-center">
          <svg
            className="h-32 w-32 text-gray-300"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>

        {/* Title */}
        <h1 className="text-4xl font-bold text-gray-900">{title}</h1>

        {/* Message */}
        <p className="text-lg text-gray-600">{message}</p>

        {/* Back Button */}
        {showBackButton && (
          <div className="pt-4">
            <Link
              href={backLink}
              className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              <svg
                className="h-5 w-5 mr-2"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 19l-7-7m0 0l7-7m-7 7h18"
                />
              </svg>
              {backText}
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
