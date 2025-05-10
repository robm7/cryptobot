import os
import sys
import json
import time
import unittest
import tempfile
import logging
import re
import unicodedata
import codecs
from datetime import datetime
from unittest import mock

# Add project root to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from token_optimization_system import (
    process_logs, 
    store_in_memory, 
    track_token_usage, 
    preprocess_data,
    analyze_memory_entities, 
    check_token_usage
)
from utils.log_processor import LogProcessor
from utils.token_optimizer import TokenOptimizer
from utils.mcp_wrapper import MCPWrapper
try:
    from utils.data_preprocessor import DataPreprocessor
except ImportError:
    # Handle case where DataPreprocessor might not be directly importable
    DataPreprocessor = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Args:
    """Mock arguments class for testing"""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class TokenSystemEndToEndTest(unittest.TestCase):
    """
    End-to-end integration tests for the Token Optimization System.
    
    These tests validate the complete token optimization workflow,
    ensuring all components work together correctly through the entire
    data processing pipeline.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        # Create temporary directories for tests
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.log_dir = os.path.join(cls.temp_dir.name, "logs")
        cls.processed_dir = os.path.join(cls.temp_dir.name, "processed")
        cls.storage_dir = os.path.join(cls.temp_dir.name, ".mcp_local_storage")
        
        # Create directories
        os.makedirs(cls.log_dir, exist_ok=True)
        os.makedirs(cls.processed_dir, exist_ok=True)
        os.makedirs(cls.storage_dir, exist_ok=True)
        
        # Create test log files of different sizes and types
        cls.regular_log_path = os.path.join(cls.log_dir, "regular_test.log")
        cls.large_log_path = os.path.join(cls.log_dir, "large_test.log")
        cls.json_log_path = os.path.join(cls.log_dir, "json_test.log")
        cls.xml_log_path = os.path.join(cls.log_dir, "xml_test.log")
        cls.mixed_log_path = os.path.join(cls.log_dir, "mixed_test.log")
        cls.code_log_path = os.path.join(cls.log_dir, "code_test.log")
        cls.unusual_encoding_log_path = os.path.join(cls.log_dir, "unusual_encoding_test.log")
        cls.repetitive_log_path = os.path.join(cls.log_dir, "repetitive_test.log")
        cls.nested_errors_log_path = os.path.join(cls.log_dir, "nested_errors_test.log")
        cls.token_boundary_log_path = os.path.join(cls.log_dir, "token_boundary_test.log")
        
        # Generate test log files
        cls._generate_regular_log(cls.regular_log_path, lines=1000)
        cls._generate_large_log(cls.large_log_path, lines=100000)  # >10MB
        cls._generate_json_log(cls.json_log_path)
        cls._generate_xml_log(cls.xml_log_path)
        cls._generate_mixed_log(cls.mixed_log_path)
        cls._generate_code_log(cls.code_log_path)
        cls._generate_unusual_encoding_log(cls.unusual_encoding_log_path)
        cls._generate_repetitive_log(cls.repetitive_log_path)
        cls._generate_nested_errors_log(cls.nested_errors_log_path)
        cls._generate_token_boundary_log(cls.token_boundary_log_path)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        cls.temp_dir.cleanup()
    
    @classmethod
    def _generate_regular_log(cls, path, lines=1000):
        """Generate a regular test log file"""
        with open(path, 'w') as f:
            for i in range(lines):
                f.write(f"[INFO] 2025-05-07 10:00:{i % 60:02d} - Processing item {i}\n")
                
                # Add warnings occasionally
                if i % 20 == 0:
                    f.write(f"[WARNING] 2025-05-07 10:00:{i % 60:02d} - Resource usage high: {60 + i % 30}%\n")
                
                # Add errors occasionally
                if i % 100 == 0:
                    error_type = ["AssertionError", "ValueError", "TypeError", "ConnectionError", "KeyError"][i % 5]
                    f.write(f"[ERROR] 2025-05-07 10:00:{i % 60:02d} - {error_type}: Something went wrong with item {i}\n")
                    
                    # Add a traceback for some errors
                    if i % 200 == 0:
                        f.write("Traceback (most recent call last):\n")
                        f.write(f'  File "test_file.py", line {i % 100 + 10}, in test_function\n')
                        f.write("    result = process_data(item)\n")
                        f.write('  File "processor.py", line 57, in process_data\n')
                        f.write("    return transform(data)\n")
                        f.write('  File "transformer.py", line 102, in transform\n')
                        f.write(f"    raise {error_type}(f'Failed to transform data: {{err}}')\n")
                        f.write(f"{error_type}: Failed to transform data: Invalid format\n\n")
    
    @classmethod
    def _generate_large_log(cls, path, lines=100000):
        """Generate a large test log file (>10MB)"""
        with open(path, 'w') as f:
            for i in range(lines):
                f.write(f"[INFO] 2025-05-07 10:00:{i % 60:02d} - Processing item {i} with extended details...\n")
                
                # Add more detailed content to make the file larger
                if i % 10 == 0:
                    f.write(f"[DETAIL] Item {i} properties: id={i*1000}, status='processing', priority={i%5}, " +
                           f"category='type-{i%10}', tags=['tag1', 'tag2', 'tag3'], timestamp='{datetime.now().isoformat()}'\n")
                
                # Add warnings occasionally
                if i % 20 == 0:
                    f.write(f"[WARNING] 2025-05-07 10:00:{i % 60:02d} - Resource usage high: {60 + i % 30}%\n")
                    f.write(f"[WARNING] Details: CPU: {40 + i % 50}%, Memory: {70 + i % 25}%, Disk: {30 + i % 60}%\n")
                
                # Add errors occasionally with detailed traces
                if i % 200 == 0:
                    error_type = ["AssertionError", "ValueError", "TypeError", "ConnectionError", "KeyError", 
                                 "RuntimeError", "IndexError", "AttributeError", "ImportError", "PermissionError"][i % 10]
                    f.write(f"[ERROR] 2025-05-07 10:00:{i % 60:02d} - {error_type}: Detailed error with item {i}\n")
                    f.write("Traceback (most recent call last):\n")
                    
                    # Generate a deeper stack trace
                    stack_depth = 5 + (i % 5)
                    for j in range(stack_depth):
                        file_name = ["main.py", "processor.py", "analyzer.py", "transformer.py", "validator.py", 
                                    "connector.py", "handler.py", "manager.py", "helper.py", "utils.py"][j % 10]
                        function_name = ["process", "validate", "transform", "handle", "analyze", "connect", 
                                        "manage", "parse", "execute", "calculate"][j % 10]
                        line_num = 10 + ((i * j) % 90)
                        f.write(f'  File "{file_name}", line {line_num}, in {function_name}\n')
                        
                        # Add some code context for the stack trace
                        if j < stack_depth - 1:
                            f.write(f"    result = {function_name}_data(item, options={{'debug': True}})\n")
                        else:
                            f.write(f"    raise {error_type}(f'Failed in {function_name}: {{detailed_error}}')\n")
                    
                    # Final error message
                    f.write(f"{error_type}: Failed in {function_name}: Validation error with code {i%100}\n\n")
    
    @classmethod
    def _generate_json_log(cls, path):
        """Generate a test log file with JSON content"""
        with open(path, 'w') as f:
            for i in range(50):
                # Add standard log entries
                f.write(f"[INFO] 2025-05-07 10:00:{i % 60:02d} - Processing JSON record {i}\n")
                
                # Add JSON objects with increasing complexity
                json_depth = (i % 5) + 1
                json_obj = cls._create_nested_json(i, depth=json_depth)
                f.write(f"[DATA] JSON object {i}:\n")
                f.write(json.dumps(json_obj, indent=2) + "\n\n")
    
    @classmethod
    def _create_nested_json(cls, seed, depth=1):
        """Helper to create nested JSON objects"""
        if depth <= 0:
            return f"value-{seed}"
            
        obj = {
            "id": seed,
            "timestamp": datetime.now().isoformat(),
            "status": ["pending", "processing", "completed", "failed", "suspended"][seed % 5],
            "metrics": {
                "duration": seed * 10.5,
                "cpu_usage": (seed % 100) / 100,
                "memory_usage": (seed % 500) + 100
            },
            "tags": [f"tag-{seed % 10}", f"priority-{seed % 5}", f"category-{seed % 3}"]
        }
        
        # Add nested objects based on depth
        if depth > 1:
            obj["children"] = [
                cls._create_nested_json(seed * 10 + i, depth - 1)
                for i in range(3)  # Limit children to prevent exponential growth
            ]
            
        return obj
    
    @classmethod
    def _generate_xml_log(cls, path):
        """Generate a test log file with XML content"""
        with open(path, 'w') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<testlog>\n')
            
            for i in range(30):
                # Add XML entries with test results
                test_status = "passed" if i % 3 != 0 else "failed"
                error_type = "" if test_status == "passed" else ["AssertionError", "ValueError", "TypeError"][i % 3]
                
                f.write(f'  <testcase id="{i}" timestamp="2025-05-07T10:{i%60:02d}:00" status="{test_status}">\n')
                f.write(f'    <name>Test Case {i}</name>\n')
                f.write(f'    <duration>{i * 0.5:.1f}</duration>\n')
                
                if test_status == "failed":
                    f.write(f'    <failure type="{error_type}">\n')
                    f.write(f'      Test {i} failed with error: Expected value to equal {i} but got {i+1}\n')
                    f.write('      <![CDATA[\n')
                    f.write('        Traceback (most recent call last):\n')
                    f.write(f'          File "test_xml.py", line {i+10}, in test_function\n')
                    f.write(f'            self.assertEqual(value, {i})\n')
                    f.write(f'        {error_type}: Expected value to equal {i} but got {i+1}\n')
                    f.write('      ]]>\n')
                    f.write('    </failure>\n')
                
                f.write('  </testcase>\n')
            
            f.write('</testlog>\n')
    
    @classmethod
    def _generate_mixed_log(cls, path):
        """Generate a test log file with mixed content types"""
        with open(path, 'w') as f:
            # Add regular log entries
            for i in range(50):
                f.write(f"[INFO] 2025-05-07 10:00:{i % 60:02d} - Processing mixed record {i}\n")
            
            # Add JSON section
            f.write("\n--- JSON SECTION START ---\n")
            json_obj = {
                "testRun": {
                    "id": 12345,
                    "timestamp": datetime.now().isoformat(),
                    "results": [
                        {"test": f"test_{i}", "status": "passed" if i % 3 != 0 else "failed"}
                        for i in range(10)
                    ],
                    "summary": {
                        "total": 10,
                        "passed": 7,
                        "failed": 3,
                        "duration": 45.6
                    }
                }
            }
            f.write(json.dumps(json_obj, indent=2) + "\n")
            f.write("--- JSON SECTION END ---\n\n")
            
            # Add XML section
            f.write("--- XML SECTION START ---\n")
            f.write('<config>\n')
            f.write('  <settings>\n')
            f.write('    <setting name="timeout" value="30"/>\n')
            f.write('    <setting name="retries" value="3"/>\n')
            f.write('    <setting name="debug" value="true"/>\n')
            f.write('  </settings>\n')
            f.write('  <connections>\n')
            f.write('    <connection id="primary" host="localhost" port="8080"/>\n')
            f.write('    <connection id="backup" host="127.0.0.1" port="8081"/>\n')
            f.write('  </connections>\n')
            f.write('</config>\n')
            f.write("--- XML SECTION END ---\n\n")
            
            # Add some code blocks
            f.write("--- PYTHON CODE SECTION START ---\n")
            f.write("def process_data(data):\n")
            f.write("    results = []\n")
            f.write("    for item in data:\n")
            f.write("        if item.get('status') == 'active':\n")
            f.write("            try:\n")
            f.write("                processed = transform_item(item)\n")
            f.write("                results.append(processed)\n")
            f.write("            except Exception as e:\n")
            f.write("                logger.error(f\"Failed to process item {item.get('id')}: {e}\")\n")
            f.write("    return results\n")
            f.write("--- PYTHON CODE SECTION END ---\n\n")
            
            # Add markdown-like documentation
            f.write("# Test Documentation\n\n")
            f.write("## Overview\n\n")
            f.write("This is a test file with *mixed* content types to evaluate the __token optimization__ system.\n\n")
            f.write("## Key Components\n\n")
            f.write("1. Regular log entries\n")
            f.write("2. JSON data structures\n")
            f.write("3. XML configuration\n")
            f.write("4. Code samples\n")
            f.write("5. Markdown documentation\n\n")
            
            # End with more log entries
            for i in range(10):
                f.write(f"[INFO] 2025-05-07 11:00:{i % 60:02d} - Finalizing mixed content test\n")
    
    @classmethod
    def _generate_code_log(cls, path):
        """Generate a test log file with complex code snippets and syntax"""
        with open(path, 'w') as f:
            # Add log header
            f.write("[INFO] 2025-05-07 10:00:00 - Starting code analysis log\n\n")
            
            # Python code with complex syntax
            f.write("--- Python Code Sample ---\n")
            f.write("""
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable, TypeVar, Generic

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

class ComplexDataStructure(Generic[T, K, V]):
    \"\"\"
    A complex data structure with generic types and multiple features.
    \"\"\"
    
    def __init__(self, 
                 initial_data: Optional[Dict[K, V]] = None, 
                 processor: Optional[Callable[[T], V]] = None):
        self.data: Dict[K, V] = initial_data or {}
        self.processor = processor or (lambda x: x)  # Default identity function
        self._observers: List[Callable[[str, K, V], None]] = []
    
    async def process_items(self, items: List[T]) -> Dict[str, Any]:
        \"\"\"Process multiple items asynchronously using complex comprehensions.\"\"\"
        results = {}
        
        # List and dictionary comprehensions with conditions
        processed = [self.processor(item) for item in items if item is not None]
        grouped = {
            f"group_{i}": [item for item in processed[i:i+10]]
            for i in range(0, len(processed), 10)
        }
        
        # Process groups in parallel
        async def process_group(group_name: str, group_items: List[V]) -> Tuple[str, List[Any]]:
            # Simulate processing delay with nested async calls
            result = await asyncio.gather(*[
                self._process_item(item) 
                for item in group_items
            ])
            return group_name, result
        
        # Use asyncio.gather to run multiple coroutines concurrently
        group_results = await asyncio.gather(*[
            process_group(name, items) 
            for name, items in grouped.items()
        ])
        
        # Update results with a dictionary comprehension
        results.update({
            name: {
                'count': len(items),
                'success_rate': sum(1 for i in items if i.get('success', False)) / len(items) if items else 0,
                'items': items
            }
            for name, items in group_results
        })
        
        # Use complex set operations and generators
        all_errors = {
            error
            for _, items in group_results
            for item in items
            for error in item.get('errors', [])
        }
        
        # Nested dictionary/list operations with conditionals
        results['summary'] = {
            'total_processed': len(processed),
            'success_count': sum(1 for _, items in group_results 
                               for item in items if item.get('success', False)),
            'error_types': [{'type': err, 'count': list(
                err for _, items in group_results
                for item in items
                for e in item.get('errors', [])
            ).count(err)} for err in all_errors]
        }
        
        return results
    
    async def _process_item(self, item: V) -> Dict[str, Any]:
        \"\"\"Internal method to process a single item.\"\"\"
        try:
            # Some complex dictionary unpacking and updates
            if isinstance(item, dict):
                base = {'success': True, 'errors': []}
                return {**base, **item, 'processed': True}
            else:
                return {'item': item, 'success': True, 'errors': [], 'processed': True}
        except Exception as e:
            return {'item': item, 'success': False, 'errors': [str(e)], 'processed': False}
            """)
            f.write("\n\n")
            
            # JavaScript/TypeScript complex syntax
            f.write("--- TypeScript Code Sample ---\n")
            f.write("""
interface GenericResponse<T> {
  data?: T;
  errors?: Array<{
    message: string;
    code: number;
    path?: string[];
  }>;
  meta: {
    processingTime: number;
    timestamp: string;
    pagination?: {
      page: number;
      perPage: number;
      total: number;
      pages: number;
    };
  };
}

type DataProcessor<T, R> = (input: T) => Promise<R>;

class DataPipelineManager<InputType, OutputType> {
  private processors: Array<DataProcessor<any, any>> = [];
  private errorHandlers: Map<string, (error: Error) => void> = new Map();
  
  constructor(
    private readonly config: {
      parallelProcessing: boolean;
      maxRetries: number;
      timeout: number;
    }
  ) {}
  
  addProcessor<T, R>(processor: DataProcessor<T, R>): void {
    this.processors.push(processor);
  }
  
  registerErrorHandler(errorType: string, handler: (error: Error) => void): void {
    this.errorHandlers.set(errorType, handler);
  }
  
  async process(input: InputType): Promise<GenericResponse<OutputType>> {
    const startTime = performance.now();
    let currentData: any = input;
    
    try {
      if (this.config.parallelProcessing) {
        // Parallel processing with complex Promise patterns
        const processingFunctions = this.processors.map(
          processor => async () => {
            const result = await Promise.race([
              processor(currentData),
              new Promise((_, reject) => 
                setTimeout(() => reject(new Error('Timeout')), this.config.timeout)
              )
            ]);
            return result;
          }
        );
        
        // Using reduce with async/await in a functional style
        currentData = await processingFunctions.reduce(
          async (dataPromise, processFn) => {
            const data = await dataPromise;
            let attempts = 0;
            let lastError: Error | null = null;
            
            while (attempts < this.config.maxRetries) {
              try {
                return await processFn(data);
              } catch (error) {
                lastError = error as Error;
                attempts++;
                // Exponential backoff
                await new Promise(resolve => 
                  setTimeout(resolve, Math.pow(2, attempts) * 100)
                );
              }
            }
            
            // Handle the error with registered handler or rethrow
            const handler = this.errorHandlers.get(lastError?.name || 'Error');
            if (handler && lastError) {
              handler(lastError);
              return data; // Continue with previous data on error
            }
            throw lastError;
          },
          Promise.resolve(currentData)
        );
      } else {
        // Sequential processing with error handling
        for (const processor of this.processors) {
          let attempts = 0;
          let success = false;
          
          while (!success && attempts < this.config.maxRetries) {
            try {
              currentData = await processor(currentData);
              success = true;
            } catch (error) {
              attempts++;
              if (attempts >= this.config.maxRetries) {
                const typedError = error as Error;
                const handler = this.errorHandlers.get(typedError.name || 'Error');
                if (handler) {
                  handler(typedError);
                  break; // Continue with previous data
                }
                throw error;
              }
              // Wait before retry with exponential backoff
              await new Promise(resolve => 
                setTimeout(resolve, Math.pow(2, attempts) * 100)
              );
            }
          }
        }
      }
      
      const endTime = performance.now();
      
      return {
        data: currentData as OutputType,
        meta: {
          processingTime: endTime - startTime,
          timestamp: new Date().toISOString()
        }
      };
    } catch (error) {
      const endTime = performance.now();
      return {
        errors: [{
          message: (error as Error).message,
          code: 500,
          path: ['process']
        }],
        meta: {
          processingTime: endTime - startTime,
          timestamp: new Date().toISOString()
        }
      };
    }
  }
}

// Example usage with complex generic types and arrow functions
const manager = new DataPipelineManager<string[], number>({
  parallelProcessing: true,
  maxRetries: 3,
  timeout: 5000
});

manager.addProcessor<string[], string[]>(async (data) => {
  return data.filter(item => item.length > 3)
    .map(item => item.toUpperCase());
});

manager.addProcessor<string[], number>(async (data) => {
  return data.reduce((sum, item) => sum + item.length, 0);
});

manager.registerErrorHandler('TypeError', (error) => {
  console.error(`Type error occurred: ${error.message}`);
});

// Process data with async/await and destructuring
(async () => {
  const { data, errors, meta } = await manager.process(['a', 'abc', 'defg', 'hijkl']);
  
  if (errors) {
    const [firstError, ...restErrors] = errors;
    console.error(`Error ${firstError.code}: ${firstError.message}`);
    if (restErrors.length > 0) {
      console.error(`And ${restErrors.length} more errors`);
    }
  } else if (data !== undefined) {
    console.log(`Processing result: ${data}`);
    console.log(`Took ${meta.processingTime.toFixed(2)}ms`);
  }
})();
            """)
            f.write("\n\n")
            
            # SQL example
            f.write("--- SQL Query Sample ---\n")
            f.write("""
WITH recursive_cte AS (
  SELECT 
    u.id AS user_id,
    u.username,
    u.created_at,
    0 AS depth,
    CAST(u.id AS VARCHAR(1000)) AS path
  FROM users u
  WHERE u.id = 1  -- Root user
  
  UNION ALL
  
  SELECT
    u.id AS user_id,
    u.username,
    u.created_at,
    rc.depth + 1 AS depth,
    rc.path || '->' || CAST(u.id AS VARCHAR(10)) AS path
  FROM users u
  JOIN referrals r ON r.referred_user_id = u.id
  JOIN recursive_cte rc ON rc.user_id = r.referrer_id
  WHERE rc.depth < 5  -- Limit depth to avoid infinite recursion
),

user_metrics AS (
  SELECT
    user_id,
    COUNT(DISTINCT o.id) AS order_count,
    SUM(CASE WHEN o.status = 'completed' THEN o.total_amount ELSE 0 END) AS total_spent,
    MAX(o.created_at) AS last_order_date,
    (
      SELECT JSON_AGG(json_build_object(
        'product_id', p.id,
        'product_name', p.name,
        'purchase_count', COUNT(oi.id)
      ))
      FROM order_items oi
      JOIN products p ON p.id = oi.product_id
      JOIN orders o2 ON o2.id = oi.order_id
      WHERE o2.user_id = user_metrics.user_id
      GROUP BY p.id
      ORDER BY COUNT(oi.id) DESC
      LIMIT 3
    ) AS top_products
  FROM recursive_cte rc
  LEFT JOIN orders o ON o.user_id = rc.user_id
  GROUP BY user_id
)

SELECT
  rc.user_id,
  rc.username,
  rc.depth,
  rc.path,
  COALESCE(um.order_count, 0) AS order_count,
  COALESCE(um.total_spent, 0) AS total_spent,
  um.last_order_date,
  um.top_products,
  (
    SELECT
      JSON_BUILD_OBJECT(
        'total_count', COUNT(DISTINCT l.id),
        'last_login', MAX(l.created_at),
        'devices', JSON_AGG(DISTINCT l.device_type)
      )
    FROM user_logins l
    WHERE l.user_id = rc.user_id
  ) AS login_stats,
  (
    SELECT
      JSONB_BUILD_OBJECT(
        'average_rating', AVG(r.rating),
        'count', COUNT(r.id)
      )
    FROM reviews r
    WHERE r.user_id = rc.user_id
  ) AS review_stats
FROM recursive_cte rc
LEFT JOIN user_metrics um ON um.user_id = rc.user_id
ORDER BY rc.depth, rc.user_id;
            """)
            f.write("\n\n")
            
            # Add log entries to wrap around code
            for i in range(10):
                f.write(f"[INFO] 2025-05-07 11:00:{i % 60:02d} - Processed code sample {i}\n")
            
            # Add some error logs about the code analysis
            f.write("[ERROR] 2025-05-07 11:30:00 - Syntax error in complex SQL query\n")
            f.write("Traceback (most recent call last):\n")
            f.write('  File "code_analyzer.py", line 123, in parse_sql\n')
            f.write("    return sql_parser.parse(query)\n")
            f.write('  File "sql_parser.py", line 45, in parse\n')
            f.write("    ast = build_ast(tokenized_query)\n")
            f.write('  File "sql_ast.py", line 67, in build_ast\n')
            f.write("    raise SyntaxError(f\"Unexpected token at position {pos}: {token}\")\n")
            f.write("SyntaxError: Unexpected token at position 1842: ')'\n\n")
            
            f.write("[INFO] 2025-05-07 11:40:00 - Completed code analysis with 3 warnings and 1 error\n")
    
    @classmethod
    def _generate_unusual_encoding_log(cls, path):
        """Generate a test log file with unusual character encodings"""
        with open(path, 'w', encoding='utf-8') as f:
            # Add log header
            f.write("[INFO] 2025-05-07 10:00:00 - Starting unusual encoding test\n\n")
            
            # Add various non-ASCII character sets
            f.write("--- UTF-8 Special Characters ---\n")
            # Add various scripts and symbols
            f.write("Arabic: مرحبا بالعالم. هذا اختبار للترميز.\n")
            f.write("Chinese: 你好，世界。这是一个编码测试.\n")
            f.write("Russian: Привет, мир. Это тест кодировки.\n")
            f.write("Greek: Γειά σου Κόσμε. Αυτή είναι μια δοκιμή κωδικοποίησης.\n")
            f.write("Japanese: こんにちは世界。これはエンコードテストです.\n")
            f.write("Korean: 안녕하세요 세계. 이것은 인코딩 테스트입니다.\n")
            f.write("Emoji: 🚀 🔍 🐛 🔄 ⚠️ ✅ ❌ 📊 🔒 🌐\n")
            f.write("Math symbols: ∑ ∫ ∂ √ ∛ ∞ ≈ ≠ ≤ ≥ ∈ ∉ ∩ ∪\n")
            f.write("Musical notes: ♩ ♪ ♫ ♬ ♭ ♮ ♯\n")
            
            # Add control characters and other problematic characters
            f.write("\n--- Control & Special Characters ---\n")
            f.write("Tab separated\tvalues\tcan\tbe\ttricky\n")
            f.write("Null byte placeholder: [\\x00]\n")
            f.write("Backspace: a\bb\n")  # This will render as "ab" but with a backspace control character
            f.write("Vertical tab: a\vb\n")
            f.write("Form feed: a\fb\n")
            f.write("Zero-width space: a\u200Bb\n")  # Invisible but can break tokenization
            f.write("Right-to-left override: English\u202Etextreverse\n")
            
            # Add UTF-16 surrogate pairs (represented in UTF-8)
            f.write("\n--- UTF-16 Surrogate Pairs (in UTF-8) ---\n")
            f.write("Surrogate Pair: \U0001F600 \U0001F64F \U0001F680\n")
            
            # Add bidirectional text mixing
            f.write("\n--- Bidirectional Text ---\n")
            f.write("Mixed direction: English with العربية and עברית mixed in\n")
            
            # Add a normalize/denormalized text sample
            sample_text = "résumé"
            normalized_nfc = unicodedata.normalize('NFC', sample_text)
            normalized_nfd = unicodedata.normalize('NFD', sample_text)
            f.write("\n--- Unicode Normalization ---\n")
            f.write(f"NFC (Composed): {normalized_nfc}\n")
            f.write(f"NFD (Decomposed): {normalized_nfd}\n")
            
            # Add extremely long line without spaces (can break tokenization)
            long_line = "x" * 5000
            f.write("\n--- Extremely Long Line ---\n")
            f.write(long_line + "\n")
            
            # Add JSON with special characters
            f.write("\n--- JSON with Special Characters ---\n")
            json_obj = {
                "title": "Encoding Test",
                "description": "Testing various Unicode characters",
                "special_chars": "§»«\u2028\u2029☺☻♠♣♥♦✈",
                "nested": {
                    "path": "C:\\Program Files\\Test\\नमस्ते.txt",
                    "quotes": "He said, \"That's mine!\"",
                    "multiline": "Line 1\nLine 2\r\nLine 3",
                }
            }
            f.write(json.dumps(json_obj, ensure_ascii=False, indent=2) + "\n")
            
            # Add log error entries
            f.write("[ERROR] 2025-05-07 10:30:00 - Failed to parse content with encoding\n")
            f.write("Traceback (most recent call last):\n")
            f.write('  File "encoder.py", line 45, in parse_content\n')
            f.write("    decoded = content.decode('ascii')\n")
            f.write("UnicodeDecodeError: 'ascii' codec can't decode byte 0xe2 in position 23: ordinal not in range(128)\n\n")
    
    @classmethod
    def _generate_repetitive_log(cls, path):
        """Generate a test log file with extreme repetition patterns"""
        with open(path, 'w') as f:
            # Repeating simple patterns
            pattern = "[INFO] 2025-05-07 10:00:00 - Operation successful\n"
            f.write(pattern * 1000)  # Repeat 1000 times
            
            # Add occasional different entries
            for i in range(20):
                position = i * 50
                f.write(f"[INFO] 2025-05-07 10:01:{i:02d} - Unique log entry at position {position}\n")
            
            # Repeating complex pattern blocks
            for i in range(100):
                f.write(f"--- Block {i} start ---\n")
                f.write("[INFO] Processing batch\n")
                f.write("[INFO] Connecting to database\n")
                f.write("[INFO] Fetching records\n")
                f.write("[INFO] Processing records\n")
                f.write("[INFO] Disconnecting from database\n")
                f.write(f"--- Block {i} end ---\n\n")
            
            # Repeating error patterns
            error_pattern = """[ERROR] 2025-05-07 10:30:00 - Connection failed
Traceback (most recent call last):
  File "connection.py", line 45, in connect
    socket.connect((host, port))
ConnectionRefusedError: [Errno 111] Connection refused

"""
            f.write(error_pattern * 50)  # Repeat 50 times
            
            # Gradually changing repetitive pattern to test pattern recognition
            for i in range(100):
                f.write(f"[INFO] 2025-05-07 {10+(i//60):02d}:{i%60:02d}:00 - Item {i} processed with result code {i%10}\n")
            
            # Random-looking but actually deterministic pattern
            for i in range(1000):
                # Use a reproducible pattern that looks random but isn't
                val1 = (i * 17) % 100
                val2 = (i * 23) % 100
                val3 = (i * 19) % 5
                
                # Format that looks varied but has underlying pattern
                types = ["INFO", "DEBUG", "TRACE", "WARNING", "ERROR"]
                log_type = types[val3]
                
                f.write(f"[{log_type}] Metric {val1} = {val2}\n")
    
    @classmethod
    def _generate_nested_errors_log(cls, path):
        """Generate a test log file with deeply nested error traces"""
        with open(path, 'w') as f:
            # Add log header
            f.write("[INFO] 2025-05-07 10:00:00 - Starting system with nested error handlers\n\n")
            
            # Create a set of nested errors with increasing complexity
            for i in range(5):
                depth = i + 3  # Starting with 3 levels and increasing
                
                f.write(f"[ERROR] 2025-05-07 10:10:00 - Nested error test case {i+1} (depth: {depth})\n")
                f.write("Traceback (most recent call last):\n")
                
                # Generate deeply nested error traces
                for j in range(depth):
                    level = depth - j
                    f.write(f'  File "level_{level}.py", line {20+j*5}, in handle_request_{level}\n')
                    
                    if j < depth - 1:
                        f.write(f"    return process_request_{level}(request)\n")
                    else:
                        f.write("    raise ValueError(\"Invalid request parameter\")\n")
                
                # Base error
                f.write("ValueError: Invalid request parameter\n\n")
                
                # Now add a nested try-except with multiple error types
                f.write(f"[ERROR] 2025-05-07 10:20:00 - Nested exception handling test case {i+1}\n")
                f.write("Traceback (most recent call last):\n")
                
                # Primary exception
                for j in range(3):
                    f.write(f'  File "outer_{j}.py", line {100+j*10}, in function_{j}\n')
                    if j < 2:
                        f.write(f"    result = process_data_{j}(data)\n")
                    else:
                        f.write("    raise ValueError(\"Primary error occurred\")\n")
                
                f.write("ValueError: Primary error occurred\n\n")
                
                f.write("During handling of the above exception, another exception occurred:\n\n")
                
                # Secondary exception
                for j in range(2):
                    f.write(f'  File "middle_{j}.py", line {50+j*5}, in exception_handler_{j}\n')
                    if j < 1:
                        f.write("    cleanup_resources()\n")
                    else:
                        f.write("    raise RuntimeError(\"Error during cleanup\")\n")
                
                f.write("RuntimeError: Error during cleanup\n\n")
                
                f.write("During handling of the above exception, another exception occurred:\n\n")
                
                # Tertiary exception
                for j in range(2):
                    f.write(f'  File "inner_{j}.py", line {30+j*3}, in final_handler_{j}\n')
                    if j < 1:
                        f.write("    log_fatal_error()\n")
                    else:
                        f.write("    raise IOError(\"Could not write to log file\")\n")
                
                f.write("IOError: Could not write to log file\n\n")
                
                # Create complex recursive error with cyclic references
                if i >= 3:
                    f.write(f"[ERROR] 2025-05-07 10:30:00 - Recursive error pattern test case {i-2}\n")
                    f.write("Traceback (most recent call last):\n")
                    
                    # Create a repeating pattern that mimics recursion
                    for j in range(20):  # Deep recursion
                        func_name = ["handle_recursive", "process_level", "execute_step"][j % 3]
                        file_name = ["recursive.py", "processor.py", "executor.py"][j % 3]
                        line_num = 100 + (j * 3) % 20
                        
                        f.write(f'  File "{file_name}", line {line_num}, in {func_name}_{j//3}\n')
                        if j < 19:
                            next_func = ["handle_recursive", "process_level", "execute_step"][(j+1) % 3]
                            f.write(f"    return {next_func}_{(j+1)//3}(data, level={j+1})\n")
                        else:
                            f.write("    raise RecursionError(\"Maximum recursion depth exceeded\")\n")
                    
                    f.write("RecursionError: Maximum recursion depth exceeded\n\n")
    
    @classmethod
    def _generate_token_boundary_log(cls, path):
        """Generate a test log file that approaches the token limit boundary"""
        # Goal: Generate a file that when processed should be close to but under 76,659 tokens
        # Estimate: Assume ~4 chars per token on average for text content
        target_chars = 76659 * 4 * 0.95  # Target 95% of limit to stay under while being close
        
        with open(path, 'w') as f:
            # Create structured log content that will be preserved by the processor
            chars_written = 0
            entry_num = 0
            
            while chars_written < target_chars:
                # Log entry with incrementing timestamp to ensure uniqueness
                timestamp = f"2025-05-07 {10 + (entry_num // 3600):02d}:{(entry_num // 60) % 60:02d}:{entry_num % 60:02d}"
                
                # Mix different log entry types to ensure they're processed
                if entry_num % 100 == 0:
                    # Add an error with stack trace (these will be preserved)
                    log_entry = f"[ERROR] {timestamp} - Failed to process item {entry_num}\n"
                    log_entry += "Traceback (most recent call last):\n"
                    log_entry += f'  File "processor.py", line 45, in process_item\n'
                    log_entry += "    result = transform(item)\n"
                    log_entry += f'  File "transformer.py", line 77, in transform\n'
                    log_entry += f"    validate_input(item)\n"
                    log_entry += f'  File "validator.py", line 23, in validate_input\n'
                    log_entry += f"    raise ValueError(f\"Invalid item format: {item}\")\n"
                    log_entry += f"ValueError: Invalid item format: {entry_num}\n\n"
                elif entry_num % 50 == 0:
                    # Add warning logs (these will be preserved)
                    log_entry = f"[WARNING] {timestamp} - Performance degradation detected: {40 + (entry_num % 30)}ms response time\n"
                elif entry_num % 10 == 0:
                    # Add structured data (these are important and will be preserved)
                    data = {
                        "id": entry_num,
                        "timestamp": timestamp,
                        "metrics": {
                            "cpu": f"{30 + (entry_num % 50)}%",
                            "memory": f"{60 + (entry_num % 30)}%",
                            "response_time": f"{10 + (entry_num % 80)}ms"
                        },
                        "status": ["ok", "degraded", "warning", "error", "critical"][entry_num % 5]
                    }
                    log_entry = f"[DATA] {timestamp} - System metrics: {json.dumps(data)}\n\n"
                else:
                    # Add regular info logs (most will be filtered out by the processor)
                    log_entry = f"[INFO] {timestamp} - Processing item {entry_num} with standard parameters\n"
                
                f.write(log_entry)
                chars_written += len(log_entry)
                entry_num += 1
                
                # Add test failure logs occasionally (these will be preserved)
                if entry_num % 500 == 0:
                    test_entry = f"=== FAILED: test_function_{entry_num//100} (test_module.py) ===\n"
                    test_entry += f"AssertionError: Expected 200 but got 404\n\n"
                    f.write(test_entry)
                    chars_written += len(test_entry)
    
    def setUp(self):
        """Set up for each test case"""
        # Create standard args for tests
        self.args = Args(
            log_file=self.regular_log_path,
            output_dir=self.processed_dir,
            max_log_size=5,
            max_logs=10,
            store_memory=False,
            analyze_memory=False,
            memory_query=None,
            token_budget=76659,
            track_usage=False,
            check_usage=False,
            preprocess=False,
            chunk_size=1000
        )
        
        # Patch MCP wrapper to use test storage location
        patcher = mock.patch.object(MCPWrapper, '_initialize_storage')
        self.mock_init_storage = patcher.start()
        self.addCleanup(patcher.stop)
        
        # Force local storage for tests
        patcher2 = mock.patch.object(MCPWrapper, '_check_mcp_availability', return_value=False)
        self.mock_check_mcp = patcher2.start()
        self.addCleanup(patcher2.stop)
        
        # Set up test storage locations
        for wrapper_instance in [MCPWrapper()]:
            wrapper_instance.memory_storage_path = os.path.join(self.storage_dir, "memory_entities.json")
            wrapper_instance.token_usage_path = os.path.join(self.storage_dir, "token_usage.json")
            
            # Initialize storage files
            with open(wrapper_instance.memory_storage_path, 'w') as f:
                json.dump({"entities": [], "relations": []}, f)
            with open(wrapper_instance.token_usage_path, 'w') as f:
                json.dump({
                    "budget": 76659,
                    "current_usage": 0,
                    "usage_history": []
                }, f)
    
    def test_complete_e2e_workflow(self):
        """Test the complete end-to-end token optimization workflow"""
        # Step 1: Process logs
        self.args.store_memory = True
        self.args.track_usage = True
        self.args.preprocess = True
        
        # Process logs
        summary, log_path = process_logs(self.args)
        
        # Verify log processing succeeded
        self.assertIsNotNone(summary)
        self.assertTrue(os.path.exists(log_path))
        self.assertGreater(summary["original_size"], 0)
        self.assertGreater(summary["processed_size"], 0)
        self.assertLess(summary["processed_size"], summary["original_size"])
        
        # Verify memory storage worked
        success = store_in_memory(summary, log_path, self.args)
        self.assertTrue(success)
        
        # Verify token tracking worked
        success, under_budget = track_token_usage(log_path, self.args)
        self.assertTrue(success)
        self.assertTrue(under_budget)
        
        # Verify preprocessing worked
        processed_data = preprocess_data(self.args)
        self.assertIsNotNone(processed_data)
        self.assertGreater(processed_data["chunks_processed"], 0)
        
        # Verify memory entities can be analyzed
        self.args.analyze_memory = True
        analyze_memory_entities(self.args)
        
        # Verify token usage check works
        self.args.check_usage = True
        check_token_usage(self.args)
        
        # Confirm token usage is within budget
        with open(os.path.join(self.storage_dir, "token_usage.json"), 'r') as f:
            usage_data = json.load(f)
            self.assertLess(usage_data["current_usage"], 76659)
    
    def test_various_content_types(self):
        """Test token optimization with various content types"""
        log_types = {
            "Regular": self.regular_log_path,
            "JSON": self.json_log_path,
            "XML": self.xml_log_path,
            "Mixed": self.mixed_log_path,
            "Code": self.code_log_path
        }
        
        results = {}
        
        # Process each log type and collect metrics
        for log_type, log_path in log_types.items():
            # Update args with current log file
            self.args.log_file = log_path
            self.args.preprocess = True
            
            # Process logs
            start_time = time.time()
            summary, output_path = process_logs(self.args)
            processing_time = time.time() - start_time
            
            # Count original and processed tokens (rough estimate)
            with open(log_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
                original_tokens = len(original_content) // 4
            
            with open(output_path, 'r', encoding='utf-8') as f:
                processed_content = f.read()
                processed_tokens = len(processed_content) // 4
            
            # Store results
            results[log_type] = {
                "original_size": summary["original_size"],
                "processed_size": summary["processed_size"],
                "compression_ratio": summary["compression_ratio"],
                "estimated_tokens": summary["estimated_tokens"],
                "original_tokens": original_tokens,
                "processed_tokens": processed_tokens,
                "token_reduction": 1 - (processed_tokens / original_tokens),
                "processing_time": processing_time
            }
            
            # Verify processed output is smaller than input
            self.assertLess(processed_tokens, original_tokens)
            
            # Verify token count stays within limit
            self.assertLess(summary["estimated_tokens"], 76659)
        
        # Compare optimization effectiveness across content types
        for log_type, metrics in results.items():
            logger.info(f"--- {log_type} Content Type Results ---")
            logger.info(f"Compression ratio: {metrics['compression_ratio']:.2%}")
            logger.info(f"Token reduction: {metrics['token_reduction']:.2%}")
            logger.info(f"Processing time: {metrics['processing_time']:.4f}s")
            logger.info(f"Estimated tokens: {metrics['estimated_tokens']}")
    
    def test_edge_case_large_file(self):
        """Test optimization with extremely large file (>10MB)"""
        # Update args to use large log file
        self.args.log_file = self.large_log_path
        
        # Process logs
        start_time = time.time()
        summary, log_path = process_logs(self.args)
        processing_time = time.time() - start_time
        
        # Verify processing completed successfully
        self.assertIsNotNone(summary)
        self.assertTrue(os.path.exists(log_path))
        
        # Verify the original file is >10MB
        original_size_mb = os.path.getsize(self.large_log_path) / (1024 * 1024)
        self.assertGreater(original_size_mb, 10, f"Test file should be >10MB, but is {original_size_mb:.2f}MB")
        
        # Check token counts
        self.assertLess(summary["estimated_tokens"], 76659)
        
        # Check efficiency metrics
        lines_per_second = summary["original_size"] / processing_time
        logger.info(f"Processing efficiency: {lines_per_second:.2f} lines/second")
        logger.info(f"Total processing time: {processing_time:.2f} seconds")
        
        # Verify system stays under token limit even with large file
        self.assertFalse(summary.get("token_limit_reached", False))
    
    def test_edge_case_very_large_entry(self):
        """Test optimization with extremely large individual entries"""
        # Create a file with some very large individual log entries
        large_entry_path = os.path.join(self.log_dir, "large_entry_test.log")
        
        with open(large_entry_path, 'w') as f:
            # Add some regular entries
            for i in range(100):
                f.write(f"[INFO] 2025-05-07 10:00:{i % 60:02d} - Regular entry {i}\n")
            
            # Add an extremely large JSON entry
            f.write("\n[DATA] Very large JSON object:\n")
            large_json = {
                "id": "large-entry-test",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "nested": {
                        "array": [
                            {
                                "item": i,
                                "value": "x" * 1000,  # 1KB string
                                "metrics": {k: k*i for k in range(100)}  # 100 metrics per item
                            }
                            for i in range(50)  # 50 large array items
                        ]
                    }
                }
            }
            f.write(json.dumps(large_json, indent=2) + "\n\n")
            
            # Add an extremely large error trace
            f.write("[ERROR] Very large stack trace:\n")
            f.write("Traceback (most recent call last):\n")
            for i in range(100):  # 100 levels deep stack trace
                f.write(f'  File "deep_call_{i}.py", line {i*10}, in function_{i}\n')
                if i < 99:
                    f.write(f"    return deep_function_{i+1}()\n")
                else:
                    f.write("    raise OverflowError('Maximum call stack depth exceeded')\n")
            f.write("OverflowError: Maximum call stack depth exceeded\n\n")
        
        # Update args to use the large entry log file
        self.args.log_file = large_entry_path
        
        # Process logs
        summary, log_path = process_logs(self.args)
        
        # Verify processing completed successfully
        self.assertIsNotNone(summary)
        self.assertTrue(os.path.exists(log_path))
        
        # Check token counts
        self.assertLess(summary["estimated_tokens"], 76659)
        
        # Verify the output still contains critical error information
        with open(log_path, 'r') as f:
            content = f.read()
            self.assertIn("OverflowError", content)
            # Should contain a truncated version of the stack trace
            self.assertIn("Traceback", content)
            # Check if content was properly truncated but key information preserved
            self.assertGreater(len(content) * 4, 1000)  # Should have some reasonable size
            self.assertLess(len(content) * 4, 76659)  # Should be under token limit
    
    def test_token_limit_enforcement(self):
        """Test system's enforcement of token limits with growing file sizes"""
        # Test with progressively larger files to find the boundary
        for i in range(5):
            # Create a log file of increasing size
            scale_factor = i + 1
            lines = 5000 * scale_factor
            
            path = os.path.join(self.log_dir, f"growing_log_{i}.log")
            
            # Generate a log file with roughly predictable token count
            with open(path, 'w') as f:
                for j in range(lines):
                    # Each line is roughly ~8-10 tokens
                    f.write(f"[INFO] 2025-05-07 10:{j//60:02d}:{j%60:02d} - Processing item {j} with details: " +
                            f"status=running, memory={50+j%30}%, cpu={30+j%60}%, disk={70+j%20}%\n")
                    
                    # Add errors occasionally to ensure they're preserved
                    if j % 500 == 0:
                        f.write(f"[ERROR] 2025-05-07 10:{j//60:02d}:{j%60:02d} - Failed to process item {j}\n")
                        f.write("Traceback (most recent call last):\n")
                        f.write(f'  File "processor.py", line 45, in process_item\n')
                        f.write(f"    result = validate(item_{j})\n")
                        f.write(f'  File "validator.py", line 23, in validate\n')
                        f.write(f"    raise ValueError(f\"Validation failed for {{item_id}}\")\n")
                        f.write(f"ValueError: Validation failed for item_{j}\n\n")
            
            # Update args to use this log file
            self.args.log_file = path
            
            # Process logs
            summary, log_path = process_logs(self.args)
            
            # Check if token limit was reached for larger files
            if i >= 3:  # The larger files should hit the token limit
                self.assertTrue(
                    summary.get("token_limit_reached", False),
                    f"Token limit should be reached for file {i} with ~{lines} lines"
                )
            
            # Even if truncated, should always be under token limit
            self.assertLess(summary["estimated_tokens"], 76659)
            
            # Check if output preserves critical information (errors) even when truncated
            with open(log_path, 'r') as f:
                content = f.read()
                # Should contain error information
                self.assertIn("ERROR", content)
                # Should indicate if truncated
                if summary.get("token_limit_reached", False):
                    self.assertIn("TOKEN LIMIT REACHED", content)
    
    def test_component_interaction(self):
        """Test interaction between different system components"""
        # Enable all components for full integration testing
        self.args.store_memory = True
        self.args.track_usage = True
        self.args.preprocess = True
        self.args.analyze_memory = True
        self.args.check_usage = True
        self.args.log_file = self.mixed_log_path  # Use mixed content for testing
        
        # Step 1: Process logs and verify success
        summary, log_path = process_logs(self.args)
        self.assertIsNotNone(summary)
        self.assertTrue(os.path.exists(log_path))
        
        # Step 2: Store in memory and verify entities created
        success = store_in_memory(summary, log_path, self.args)
        self.assertTrue(success)
        
        # Check if entities were properly stored
        with open(os.path.join(self.storage_dir, "memory_entities.json"), 'r') as f:
            memory_data = json.load(f)
            self.assertGreater(len(memory_data["entities"]), 0)
            self.assertGreater(len(memory_data["relations"]), 0)
        
        # Step 3: Track token usage and verify below budget
        success, under_budget = track_token_usage(log_path, self.args)
        self.assertTrue(success)
        self.assertTrue(under_budget)
        
        # Check if token usage is properly tracked
        with open(os.path.join(self.storage_dir, "token_usage.json"), 'r') as f:
            usage_data = json.load(f)
            self.assertGreater(usage_data["current_usage"], 0)
            self.assertLess(usage_data["current_usage"], 76659)
            self.assertGreater(len(usage_data["usage_history"]), 0)
        
        # Step 4: Preprocess data and verify chunking works
        processed_data = preprocess_data(self.args)
        self.assertIsNotNone(processed_data)
        self.assertGreater(processed_data["chunks_processed"], 0)
        
        # Step 5: Analyze memory and check token usage - these are more UI functions
        # so we're mainly checking they don't error
        analyze_memory_entities(self.args)
        check_token_usage(self.args)
    
    def test_unusual_encodings(self):
        """Test system's handling of unusual character encodings"""
        # Update args to use the unusual encoding log
        self.args.log_file = self.unusual_encoding_log_path
        
        # Process logs
        summary, log_path = process_logs(self.args)
        
        # Verify processing completed successfully
        self.assertIsNotNone(summary)
        self.assertTrue(os.path.exists(log_path))
        
        # Check if the processed file preserved important content
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Check for preservation of error messages with encoding references
            self.assertIn("UnicodeDecodeError", content)
            
            # Check file was processed without encoding errors
            self.assertIn("Starting unusual encoding test", content)
            
            # Check token counts
            self.assertLess(summary["estimated_tokens"], 76659)
    
    def test_repetitive_patterns(self):
        """Test system's handling of extremely repetitive log patterns"""
        # Update args to use the repetitive log
        self.args.log_file = self.repetitive_log_path
        
        # Process logs
        summary, log_path = process_logs(self.args)
        
        # Verify processing completed successfully
        self.assertIsNotNone(summary)
        self.assertTrue(os.path.exists(log_path))
        
        # Check compression is particularly effective for repetitive patterns
        self.assertGreater(summary["compression_ratio"], 0.9, 
                          "Compression ratio should be very high for repetitive patterns")
        
        # Verify the output still contains critical information
        with open(log_path, 'r') as f:
            content = f.read()
            # Should contain error information even though repetitive
            self.assertIn("ConnectionRefusedError", content)
            
            # Check token counts are well under budget despite large input
            self.assertLess(summary["estimated_tokens"], 76659 // 2)
    
    def test_nested_errors(self):
        """Test system's handling of deeply nested error traces"""
        # Update args to use the nested errors log
        self.args.log_file = self.nested_errors_log_path
        
        # Process logs
        summary, log_path = process_logs(self.args)
        
        # Verify processing completed successfully
        self.assertIsNotNone(summary)
        self.assertTrue(os.path.exists(log_path))
        
        # Check if output preserved the complex nested error structure
        with open(log_path, 'r') as f:
            content = f.read()
            
            # Basic error info should be present
            self.assertIn("ValueError", content)
            self.assertIn("RuntimeError", content)
            self.assertIn("IOError", content)
            
            # Should preserve the "during handling of above exception" markers
            self.assertIn("another exception occurred", content.lower())
            
            # RecursionError from the deep recursive case should be present
            self.assertIn("RecursionError", content)
            
            # Check token counts
            self.assertLess(summary["estimated_tokens"], 76659)
    
    def test_token_boundary_optimization(self):
        """Test system behavior with content approaching token limit boundary"""
        # Update args to use the token boundary log
        self.args.log_file = self.token_boundary_log_path
        
        # Process logs
        summary, log_path = process_logs(self.args)
        
        # Verify processing completed successfully
        self.assertIsNotNone(summary)
        self.assertTrue(os.path.exists(log_path))
        
        # Check if close to but under token limit
        self.assertGreater(summary["estimated_tokens"], 76659 * 0.8)  # Should use at least 80% of budget
        self.assertLess(summary["estimated_tokens"], 76659)  # But stay under the limit
        
        # Enable all components to ensure they work with near-boundary content
        self.args.store_memory = True
        self.args.track_usage = True
        
        # Test memory storage with large content
        success = store_in_memory(summary, log_path, self.args)
        self.assertTrue(success)
        
        # Test token tracking with large content
        success, under_budget = track_token_usage(log_path, self.args)
        self.assertTrue(success)
        self.assertTrue(under_budget)
        
        # Verify token count is accurately tracked
        with open(os.path.join(self.storage_dir, "token_usage.json"), 'r') as f:
            usage_data = json.load(f)
            # Should be close to but below the budget
            self.assertGreater(usage_data["current_usage"], 76659 * 0.8)
            self.assertLess(usage_data["current_usage"], 76659)
    
    def test_integrated_memory_token_tracking(self):
        """Test that memory storage and token tracking work together properly"""
        # Initialize token usage to zero
        with open(os.path.join(self.storage_dir, "token_usage.json"), 'w') as f:
            json.dump({
                "budget": 76659,
                "current_usage": 0,
                "usage_history": []
            }, f)
        
        # Process multiple files in sequence to test accumulation
        test_files = [
            self.regular_log_path,
            self.json_log_path,
            self.xml_log_path
        ]
        
        entities_count = 0
        cumulative_tokens = 0
        
        for log_path in test_files:
            # Update args for current file
            self.args.log_file = log_path
            self.args.store_memory = True
            self.args.track_usage = True
            
            # Process logs
            summary, output_path = process_logs(self.args)
            
            # Store in memory
            success = store_in_memory(summary, output_path, self.args)
            self.assertTrue(success)
            
            # Track token usage 
            success, under_budget = track_token_usage(output_path, self.args)
            self.assertTrue(success)
            self.assertTrue(under_budget)
            
            # Get current memory and token stats
            with open(os.path.join(self.storage_dir, "memory_entities.json"), 'r') as f:
                memory_data = json.load(f)
                current_entities = len(memory_data["entities"])
                self.assertGreater(current_entities, entities_count, 
                                  "Number of entities should increase with each processed file")
                entities_count = current_entities
            
            with open(os.path.join(self.storage_dir, "token_usage.json"), 'r') as f:
                usage_data = json.load(f)
                current_tokens = usage_data["current_usage"]
                self.assertGreater(current_tokens, cumulative_tokens, 
                                  "Token usage should increase with each processed file")
                cumulative_tokens = current_tokens
        
        # Check final values
        self.assertGreater(entities_count, 0, "Should have stored multiple entities")
        self.assertGreater(cumulative_tokens, 0, "Should have tracked token usage")
        self.assertLess(cumulative_tokens, 76659, "Total usage should remain under budget")