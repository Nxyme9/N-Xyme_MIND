use std::fs;
use std::path::Path;
use std::env;

fn main() {
    let args: Vec<String> = env::args().collect();
    let base_dir = if args.len() > 1 {
        args[1].clone()
    } else {
        env::current_dir().unwrap().to_string_lossy().to_string()
    };

    let agents_dir = Path::new(&base_dir).join("agents");
    let output_dir = Path::new(&base_dir).join(".opencode").join("agents");

    // Create output directory if it doesn't exist
    if !output_dir.exists() {
        fs::create_dir_all(&output_dir).expect("Failed to create .opencode/agents directory");
        println!("Created directory: {:?}", output_dir);
    }

    // Read all agent.js files
    let mut agent_count = 0;

    if let Ok(entries) = fs::read_dir(&agents_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                let agent_js = path.join("agent.js");
                if agent_js.exists() {
                    let agent_name = path.file_name()
                        .map(|n| n.to_string_lossy().to_string())
                        .unwrap_or_default();

                    println!("Processing agent: {}", agent_name);

                    match parse_agent_js(&agent_js) {
                        Ok((name, mode, model, description, prompt)) => {
                            let output_file = output_dir.join(format!("{}.md", agent_name));
                            let markdown = generate_markdown(&name, &mode, &model, &description, &prompt);

                            match fs::write(&output_file, &markdown) {
                                Ok(_) => {
                                    println!("  Generated: {:?}", output_file);
                                    agent_count += 1;
                                }
                                Err(e) => {
                                    eprintln!("  Error writing {}: {}", agent_name, e);
                                }
                            }
                        }
                        Err(e) => {
                            eprintln!("  Error parsing {}: {}", agent_name, e);
                        }
                    }
                }
            }
        }
    }

    println!("\n✓ Generated {} agent markdown files", agent_count);
}

fn parse_agent_js(path: &Path) -> Result<(String, String, String, String, String), String> {
    let content = fs::read_to_string(path)
        .map_err(|e| format!("Failed to read file: {}", e))?;

    // Extract name
    let name = extract_field(&content, "name:")
        .ok_or("Failed to extract name")?;

    // Extract mode
    let mode = extract_field(&content, "mode:")
        .ok_or("Failed to extract mode")?;

    // Extract model
    let model = extract_field(&content, "model:")
        .ok_or("Failed to extract model")?;

    // Extract description
    let description = extract_field(&content, "description:")
        .ok_or("Failed to extract description")?;

    // Extract prompt (template literal)
    let prompt = extract_template_literal(&content, "prompt:")
        .ok_or("Failed to extract prompt")?;

    Ok((name, mode, model, description, prompt))
}

fn extract_field(content: &str, field: &str) -> Option<String> {
    // Find the line containing the field
    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with(field) {
            // Extract value from "field: "value""
            if let Some(start) = trimmed.find(": \"") {
                let value_start = start + 3;
                if let Some(end) = trimmed[..value_start].rfind('"') {
                    // Find the closing quote
                    if let Some(close_quote) = trimmed[value_start..].find('"') {
                        return Some(trimmed[value_start..value_start + close_quote].to_string());
                    }
                }
            }
        }
    }
    None
}

fn extract_template_literal(content: &str, field: &str) -> Option<String> {
    // Find the field and then the opening backtick
    let field_pos = content.find(field)?;
    let after_field = &content[field_pos..];
    
    // Find opening backtick (prompt: `)
    let backtick_start = after_field.find("`")? + 1;
    let after_backtick = &after_field[backtick_start..];
    
    // Find closing backtick (the one that ends the template)
    // Need to be careful: template literals can contain backticks inside ${} but here we have simple prompts
    let backtick_end = after_backtick.find("`")?;
    
    Some(after_backtick[..backtick_end].to_string())
}

fn generate_markdown(name: &str, mode: &str, model: &str, description: &str, prompt: &str) -> String {
    let mut output = String::new();
    output.push_str("---\n");
    output.push_str(&format!("name: \"{}\"\n", name));
    output.push_str(&format!("description: \"{}\"\n", description));
    output.push_str(&format!("mode: \"{}\"\n", mode));
    output.push_str(&format!("model: \"{}\"\n", model));
    output.push_str("---\n\n");
    output.push_str(prompt);
    output
}