import React from 'react';

export default function StepProgressBar({ steps, currentStep, goToStep }) {
  const totalSteps = steps.length;

  return (
    <div className="w-full py-4 px-2 sm:px-0 mb-8"> {/* Added mb-8 back for consistency with original spacing */}
      <div className="relative">
        {/* Progress Line Background */}
        <div className="absolute left-0 top-1/2 w-full h-1 bg-gray-300 transform -translate-y-1/2" style={{ zIndex: 1 }}></div>
        {/* Progress Line Foreground */}
        <div
          className="absolute left-0 top-1/2 h-1 bg-indigo-600 transform -translate-y-1/2 transition-all duration-500 ease-in-out"
          style={{
            width: totalSteps > 1 ? `${((currentStep - 1) / (totalSteps - 1)) * 100}%` : '0%', // Handle single step case
            zIndex: 2
          }}
        ></div>

        <div className="flex items-start justify-between relative" style={{ zIndex: 3 }}> {/* items-start for label alignment */}
          {steps.map((step, index) => {
            const stepNumber = index + 1;
            const isActive = stepNumber === currentStep;
            const isCompleted = stepNumber < currentStep;
            // Allow navigation to completed, current, or the immediate next step if current is not the last
            const canNavigate = isCompleted || isActive || (stepNumber === currentStep + 1 && currentStep < totalSteps);

            return (
              <div
                key={stepNumber}
                className="flex flex-col items-center text-center"
                style={{ width: `${100 / totalSteps}%` }} // Distribute width evenly
              >
                <button
                  onClick={() => canNavigate && goToStep(stepNumber)}
                  disabled={!canNavigate}
                  className={`w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center text-sm sm:text-base font-medium transition-all duration-300 ease-in-out border-2
                    ${
                      isActive
                        ? 'bg-indigo-600 text-white border-indigo-700 ring-2 ring-offset-2 ring-indigo-500 scale-110'
                        : isCompleted
                        ? 'bg-green-500 text-white border-green-600 hover:bg-green-600'
                        : 'bg-gray-100 text-gray-500 border-gray-300 hover:bg-gray-200'
                    }
                    ${!canNavigate ? 'cursor-not-allowed opacity-70' : 'cursor-pointer'}
                  `}
                >
                  {isCompleted ? (
                    <svg className="w-5 h-5 sm:w-6 sm:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    stepNumber
                  )}
                </button>
                <span className={`mt-2 text-xs sm:text-sm font-medium transition-colors duration-300 w-full break-words px-1
                  ${isActive ? 'text-indigo-700 font-semibold' : isCompleted ? 'text-green-700' : 'text-gray-500'}
                `}>
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}