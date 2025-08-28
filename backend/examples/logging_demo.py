#!/usr/bin/env python3
"""
Example script demonstrating AndroidZen Pro comprehensive logging system.
Shows various logging features including performance monitoring, error tracking, and structured logging.
"""

import asyncio
import time
import random
from typing import Dict, Any

from .core.logging_config import (
    setup_logging,
    get_logger,
    performance_monitor,
    log_exceptions,
    set_request_context,
    clear_request_context,
    LogContext
)


class DemoService:
    """Demo service to show logging features."""
    
    def __init__(self):
        self.logger = get_logger("demo_service")
    
    @performance_monitor("database_query")
    @log_exceptions("demo_service")
    async def simulate_database_query(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Simulate a database query with performance monitoring."""
        
        # Simulate variable response times
        delay = random.uniform(0.1, 2.0)
        
        self.logger.info(f"Executing database query: {query}", 
                        context={
                            "query": query,
                            "params": params,
                            "operation_type": "database_query"
                        })
        
        await asyncio.sleep(delay)
        
        # Simulate occasional errors
        if random.random() < 0.1:  # 10% error rate
            raise Exception(f"Database connection timeout after {delay:.2f}s")
        
        result = {
            "rows": random.randint(1, 100),
            "execution_time": delay,
            "query": query
        }
        
        self.logger.info(f"Query completed successfully", 
                        context={
                            "query": query,
                            "rows_returned": result["rows"],
                            "execution_time": delay
                        })
        
        return result
    
    @log_exceptions("demo_service")
    def simulate_cpu_intensive_task(self, iterations: int = 1000000) -> float:
        """Simulate CPU-intensive task."""
        
        with self.logger.performance_context("cpu_intensive_task", 
                                           context={"iterations": iterations},
                                           tags={"task_type": "computation"}):
            
            self.logger.info(f"Starting CPU-intensive task with {iterations} iterations")
            
            # Simulate CPU work
            total = 0
            for i in range(iterations):
                total += i ** 0.5
                
                # Log progress every 100k iterations
                if i % 100000 == 0 and i > 0:
                    progress = (i / iterations) * 100
                    self.logger.debug(f"Progress: {progress:.1f}%", 
                                    context={"progress": progress, "iteration": i})
            
            self.logger.info(f"CPU-intensive task completed", 
                           context={"total": total, "iterations": iterations})
            
            return total
    
    def demonstrate_different_log_levels(self):
        """Demonstrate different log levels and contexts."""
        
        # Set some context
        LogContext.set(user_id="demo_user", session_id="demo_session")
        
        self.logger.debug("Debug message - detailed information for troubleshooting",
                         context={"debug_info": {"variable_x": 42, "state": "active"}})
        
        self.logger.info("Info message - general information about application flow",
                        context={"event": "user_action", "action": "button_click"})
        
        self.logger.warning("Warning message - something unusual happened",
                          context={"warning_type": "rate_limit", "attempts": 3})
        
        # Simulate error with context
        try:
            raise ValueError("This is a demo error")
        except ValueError as e:
            self.logger.error("Error occurred during demo", 
                            context={"error_context": "demo_function", "user_input": "invalid_data"})
        
        # Clear context
        LogContext.clear()
    
    async def simulate_user_request(self, user_id: str, action: str):
        """Simulate a user request with full context logging."""
        
        request_id = f"req_{random.randint(1000, 9999)}"
        
        # Set request context
        set_request_context(
            request_id=request_id,
            user_id=user_id,
            session_id=f"sess_{user_id}"
        )
        
        try:
            self.logger.info(f"Processing user request: {action}", 
                           context={"action": action, "user_id": user_id})
            
            # Simulate some processing
            if action == "get_devices":
                await self.simulate_database_query("SELECT * FROM devices WHERE user_id = ?", 
                                                 {"user_id": user_id})
            elif action == "analyze_storage":
                self.simulate_cpu_intensive_task(500000)
            elif action == "error_test":
                raise Exception("Simulated user request error")
            
            self.logger.info(f"Request completed successfully: {action}")
            
        except Exception as e:
            self.logger.exception(f"Request failed: {action}", 
                                context={"error": str(e), "action": action})
        finally:
            clear_request_context()


async def demonstrate_logging_system():
    """Main demonstration function."""
    
    # Setup logging with console format for demo
    logger = setup_logging(
        app_name="logging-demo",
        log_level="DEBUG",
        log_format="console",  # Use console format for better readability
        log_file="./logs/demo.log"  # Also log to file
    )
    
    logger.info("=== AndroidZen Pro Logging System Demo ===")
    logger.info("This demo showcases various logging features")
    
    # Create demo service
    service = DemoService()
    
    # 1. Demonstrate basic logging levels and contexts
    logger.info("1. Demonstrating different log levels and contexts")
    service.demonstrate_different_log_levels()
    
    # 2. Demonstrate performance monitoring
    logger.info("\n2. Demonstrating performance monitoring")
    for i in range(3):
        try:
            result = await service.simulate_database_query(f"SELECT * FROM table_{i}")
            logger.info(f"Query {i} result: {result['rows']} rows")
        except Exception as e:
            logger.error(f"Query {i} failed: {e}")
    
    # 3. Demonstrate CPU monitoring
    logger.info("\n3. Demonstrating CPU-intensive task monitoring")
    result = service.simulate_cpu_intensive_task(200000)
    logger.info(f"CPU task result: {result}")
    
    # 4. Demonstrate user request simulation
    logger.info("\n4. Demonstrating user request context logging")
    users = ["user_123", "user_456", "user_789"]
    actions = ["get_devices", "analyze_storage", "error_test"]
    
    for user in users:
        for action in actions:
            try:
                await service.simulate_user_request(user, action)
                await asyncio.sleep(0.1)  # Small delay between requests
            except Exception:
                pass  # Errors are already logged
    
    # 5. Show performance metrics
    logger.info("\n5. Performance metrics summary")
    metrics = logger.performance_monitor.get_metrics(limit=10)
    
    if metrics:
        logger.info(f"Collected {len(metrics)} performance metrics:")
        for metric in metrics[:5]:  # Show first 5 metrics
            logger.info(f"  - {metric.metric_name}: {metric.value:.2f} {metric.unit}")
    else:
        logger.info("No performance metrics collected yet")
    
    # 6. Show error summary
    logger.info("\n6. Error tracking summary")
    error_summary = logger.error_tracker.get_error_summary()
    logger.info(f"Total errors: {error_summary['total_errors']}")
    logger.info(f"Error types: {error_summary['error_types']}")
    
    if error_summary['error_counts']:
        logger.info("Error counts by type:")
        for error_type, count in error_summary['error_counts'].items():
            logger.info(f"  - {error_type}: {count}")
    
    logger.info("\n=== Demo completed ===")
    logger.info("Check the log file at ./logs/demo.log for structured JSON logs")


if __name__ == "__main__":
    print("Starting AndroidZen Pro Logging System Demo...")
    print("This will demonstrate various logging features including:")
    print("- Structured logging with context")
    print("- Performance monitoring")
    print("- Error tracking")
    print("- Request context management")
    print("- Different log levels and formatters")
    print("\nRunning demo...\n")
    
    asyncio.run(demonstrate_logging_system())
    
    print("\nDemo completed! Check the console output above and the log files for examples.")
    print("The structured JSON logs in ./logs/demo.log can be processed by log analysis tools.")

