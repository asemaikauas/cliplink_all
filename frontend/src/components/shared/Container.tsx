interface ContainerProps {
    children: React.ReactNode; 
    className?: string; 
}

export const Container = ({ children, className = ""}: ContainerProps) => {
    return (
        <div 
        className={`mx-auto max-w-7xl w-full px-5 sm:px-5 md:px-14 lg:px-5 ${className}`}>{children}
        </div>
    ); 
}; 


