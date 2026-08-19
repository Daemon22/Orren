use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RealizationState {
    values: BTreeMap<String, String>,
}

impl RealizationState {
    pub fn new(application: impl Into<String>, input_title: impl Into<String>) -> Self {
        let mut values = BTreeMap::new();
        values.insert("application".to_string(), application.into());
        values.insert("input_title".to_string(), input_title.into());
        Self { values }
    }

    pub fn insert(&mut self, key: impl Into<String>, value: impl Into<String>) {
        self.values.insert(key.into(), value.into());
    }

    pub fn get(&self, key: &str) -> Option<&str> {
        self.values.get(key).map(String::as_str)
    }

    pub fn to_records(&self) -> Vec<String> {
        self.values.iter().map(|(key, value)| format!("{key}={value}")).collect()
    }

    pub fn to_json_object(&self) -> String {
        let fields = self.values.iter().map(|(key, value)| {
            format!("\"{}\":\"{}\"", escape(key), escape(value))
        }).collect::<Vec<_>>().join(",");
        format!("{{{fields}}}")
    }
}

fn escape(value: &str) -> String {
    value.replace('\\', "\\\\").replace('"', "\\\"")
}

pub fn process(application: &str, input_title: &str) -> RealizationState {
    RealizationState::new(application, input_title)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn records_are_deterministic() {
        let mut state = process("app", "input");
        state.insert("z", "last");
        state.insert("a", "first");
        assert_eq!(state.to_records(), vec!["a=first", "application=app", "input_title=input", "z=last"]);
    }

    #[test]
    fn json_escapes_values() {
        let mut state = process("app", "quote\"slash\\");
        state.insert("x", "ok");
        assert!(state.to_json_object().contains("quote\\\"slash\\\\"));
    }
}
