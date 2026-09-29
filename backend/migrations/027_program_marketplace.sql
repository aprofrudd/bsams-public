-- Migration 027: Program Marketplace
-- Adds program_packages, program_templates, program_installations tables

-- Program packages (marketplace-visible programs)
CREATE TABLE program_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_by UUID NOT NULL REFERENCES profiles(id),
    program_name TEXT NOT NULL UNIQUE,
    description TEXT,
    category TEXT NOT NULL DEFAULT 'General',
    cover_image_url TEXT,
    is_published BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Program templates (session templates within a program)
CREATE TABLE program_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    program_id UUID NOT NULL REFERENCES program_packages(id) ON DELETE CASCADE,
    template_name TEXT NOT NULL,
    training_type TEXT NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    exercises JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(program_id, template_name)
);

-- Program installations (tracks who has access)
CREATE TABLE program_installations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    program_id UUID NOT NULL REFERENCES program_packages(id) ON DELETE CASCADE,
    installed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, program_id)
);

-- Indexes
CREATE INDEX idx_program_packages_published ON program_packages(is_published);
CREATE INDEX idx_program_packages_category ON program_packages(category);
CREATE INDEX idx_program_templates_program ON program_templates(program_id);
CREATE INDEX idx_program_installations_user ON program_installations(user_id);
CREATE INDEX idx_program_installations_program ON program_installations(program_id);

-- RLS policies (defense-in-depth)
ALTER TABLE program_packages ENABLE ROW LEVEL SECURITY;
ALTER TABLE program_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE program_installations ENABLE ROW LEVEL SECURITY;

-- Anyone can read published programs
CREATE POLICY "Anyone can read published programs"
    ON program_packages FOR SELECT
    USING (is_published = true);

-- Admins can manage all programs
CREATE POLICY "Admins manage programs"
    ON program_packages FOR ALL
    USING (
        EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
    );

-- Anyone can read templates of published programs
CREATE POLICY "Anyone can read published program templates"
    ON program_templates FOR SELECT
    USING (
        EXISTS (SELECT 1 FROM program_packages WHERE id = program_id AND is_published = true)
    );

-- Admins can manage all templates
CREATE POLICY "Admins manage program templates"
    ON program_templates FOR ALL
    USING (
        EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
    );

-- Users can manage own installations
CREATE POLICY "Users manage own installations"
    ON program_installations FOR ALL
    USING (user_id = auth.uid());

-- Anyone can read installations (for counting)
CREATE POLICY "Anyone can read installations"
    ON program_installations FOR SELECT
    USING (true);
